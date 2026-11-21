"""Freeze a rescue selection; extract a separate raw crop-candidate bank on macOS/Linux."""
import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from contextlib import contextmanager
from datetime import datetime, timezone
try:
    import fcntl
except ImportError:  # Windows does not provide Unix fcntl; batch output_lock requires POSIX.
    fcntl = None
import hashlib
from importlib.metadata import version
import json
import math
import multiprocessing
import os
from pathlib import Path
import platform
import signal
import sys
import tempfile
import traceback
from uuid import uuid4

import cv2
import numpy as np

from batch_io import MetadataResolver, completion, manifest_row, error_event
from extract_raw import load_raw, sha256
from pilot_extraction import upper_body_crop, map_crop

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = Path(__file__).with_name('rescue_policy.json')
DEFAULT_SELECTION = ROOT / 'dataset/metadata/rescue_selection.v1.json'
SCHEMA = 'vsl400.crop_candidates.v1'
CANDIDATES = ('hand_candidate_xyz', 'hand_candidate_world_xyz',
              'hand_candidate_label', 'hand_candidate_score')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def json_hash(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    atomic_write(path, lambda stream: stream.write((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode()))


def atomic_write(path, writer):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            writer(stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_policy(path):
    policy = json.loads(Path(path).read_text())
    # Restrict this version to the user-approved, piloted condition.
    if (policy.get('schema') != 'vsl400.rescue_policy.v1' or
        policy.get('version') != 'nohand20_gap400_crop060_tracking_v1' or
        policy.get('selection') != dict(no_hand_fraction_gt=.2, longest_gap_seconds_gte=.4, view='front') or
        policy.get('crop') != dict(padding_shoulder_width=.6, pose_visibility_min=.5, uses_whole_clip_pose=True) or
        policy.get('static_image_mode') is not False or policy.get('input_mirrored') is not False or
        policy.get('hands') != dict(model_complexity=1, max_num_hands=2, min_detection_confidence=.5, min_tracking_confidence=.5)):
        raise ValueError('Policy differs from approved v1; create a separately versioned condition')
    return policy


def selected(profile, policy):
    rule = policy['selection']
    return (profile['view'] == rule['view'] and
            profile['no_hand_fraction'] > rule['no_hand_fraction_gt'] and
            profile['longest_gap_seconds'] >= rule['longest_gap_seconds_gte'])


def relative(path, root):
    return Path(path).resolve().relative_to(root.resolve()).as_posix()


def project_path(root, value):
    p = (root / value).resolve()
    if not p.is_relative_to(root.resolve()):
        raise ValueError(f'Path outside project: {value}')
    return p


def detector_profile(arrays, fps):
    counts = np.diff(arrays['hand_candidate_offsets'])
    missing = counts == 0
    edges = np.diff(np.r_[False, missing, False].astype(np.int8))
    lengths = np.flatnonzero(edges == -1) - np.flatnonzero(edges == 1)
    return dict(no_hand_fraction=float(missing.mean()),
                longest_gap_seconds=int(lengths.max()) / fps if len(lengths) else 0.)


def validate_source(record, root, policy, resolver=None):
    raw = project_path(root, record['source_raw'])
    if sha256(raw) != record['source_raw_sha256']:
        raise ValueError(f'Raw source changed: {raw}')
    arrays, meta = load_raw(raw)
    if meta['schema'] != 'vsl400.detector_raw.v3' or 'hand_candidate_offsets' not in arrays:
        raise ValueError('Rescue requires complete v3 raw candidates')
    for field in ('source_part', 'view', 'video_id', 'signer_id', 'gloss'):
        if meta[field] != record[field]:
            raise ValueError(f'Source identity differs: {field}')
    video = project_path(root, record['source_video'])
    if Path(meta['source_path']).resolve() != video or sha256(video) != record['source_video_sha256']:
        raise ValueError(f'Video source changed: {video}')
    if meta['source_sha256'] != record['source_video_sha256']:
        raise ValueError('Raw/video hashes disagree')
    official = (resolver or MetadataResolver()).resolve(video)
    if (official['metadata_sha256'] != record['metadata_sha256'] or
        official['official_metadata'] != meta['official_metadata']):
        raise ValueError('Official metadata changed')
    complete, _ = completion(meta, official['official_metadata'])
    if meta['completion_status'] != 'complete' or not complete or meta['decoded_frames'] != record['frames']:
        raise ValueError('Source raw is incomplete')
    if not math.isclose(meta['fps'],record['fps'],rel_tol=1e-10,abs_tol=1e-10):
        raise ValueError('Frozen FPS differs from raw')
    measured = detector_profile(arrays, meta['fps'])
    if not selected(dict(measured, view=record['view']), policy):
        raise ValueError('Source no longer satisfies selection rule')
    if any(not math.isclose(measured[k], record[k], abs_tol=1e-10, rel_tol=1e-10) for k in measured):
        raise ValueError('Frozen screening metrics disagree with raw')
    return arrays, meta, video


def freeze_selection(profiles, survey, target, policy, root, expected_count):
    if target.exists():
        raise ValueError('Selection already exists; v1 is immutable, use a new filename/version')
    records = json.loads(profiles.read_text())
    summary = json.loads(survey.read_text())
    for name, checksum in summary['source_hashes'].items():
        if sha256(project_path(root, name)) != checksum:
            raise ValueError(f'Survey input changed: {name}')
    chosen = [r for r in records if selected(r, policy)]
    if len(chosen) != expected_count:
        raise ValueError(f'Expected {expected_count} selected clips, got {len(chosen)}')
    resolver = MetadataResolver()
    result = []
    for row in sorted(chosen, key=lambda r: (r['source_part'], r['video_id'])):
        raw = Path(row['npz'])
        _, meta = load_raw(raw)
        record = {k: meta[k] for k in ('source_part','view','video_id','signer_id','gloss')}
        record.update(source_raw=relative(raw, root), source_raw_sha256=sha256(raw),
                      source_video=relative(meta['source_path'], root), source_video_sha256=meta['source_sha256'],
                      source_metadata=relative(meta['source_metadata'], root), metadata_sha256=meta['metadata_sha256'],
                      frames=meta['decoded_frames'], fps=meta['fps'],
                      no_hand_fraction=row['no_hand_fraction'], longest_gap_seconds=row['longest_gap_seconds'])
        validate_source(record, root, policy, resolver)
        result.append(record)
    keys = [(r['source_part'],r['view'],r['video_id']) for r in result]
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate selected identity')
    document = dict(schema='vsl400.rescue_selection.v1', created_utc=now(),
                    authorization='User approved no_hand_fraction > 0.20 AND longest_gap_seconds >= 0.40 on 2026-11-07',
                    policy=policy, policy_sha256=json_hash(policy), count=len(result),
                    screening_scope='Whole clip, including rest; does not assert active-phase ground truth',
                    source_profiles=dict(path=relative(profiles,root),sha256=sha256(profiles)),
                    source_survey=dict(path=relative(survey,root),sha256=sha256(survey)), records=result)
    atomic_json(target, document)
    return document


def read_selection(path, policy):
    doc = json.loads(Path(path).read_text())
    if (doc.get('schema') != 'vsl400.rescue_selection.v1' or doc.get('policy') != policy or
        doc.get('policy_sha256') != json_hash(policy) or doc.get('count') != len(doc['records'])):
        raise ValueError('Selection/policy mismatch')
    keys = []
    for r in doc['records']:
        if not selected(r,policy) or r['view'] != 'front':
            raise ValueError('Selection contains an ineligible clip')
        keys.append((r['source_part'],r['view'],r['video_id']))
    if len(set(keys)) != len(keys):
        raise ValueError('Duplicate selected identity')
    return doc


def output_path(root, record):
    part, clip = record['source_part'], record['video_id']
    if not part.startswith('Part_') or not part[5:].isdigit() or not clip.isdigit():
        raise ValueError('Invalid output identity')
    return root / part / 'front_view' / (clip + '.mp4.crop.npz')


def check_output_location(out, records, root):
    # New bank must not contain or be inside the original video/raw banks.
    banks = {project_path(root, r['source_raw']).parent.parent.parent for r in records}
    banks |= {project_path(root, r['source_video']).parent.parent.parent for r in records}
    for bank in banks:
        if out == bank or out.is_relative_to(bank) or bank.is_relative_to(out):
            raise ValueError(f'Output must be separate from source bank: {bank}')


def runtime_info():
    return dict(python=platform.python_version(), mediapipe=version('mediapipe'), numpy=np.__version__, opencv=cv2.__version__)


def code_identity():
    return {p.name:sha256(p) for p in (Path(__file__), Path(__file__).with_name('pilot_extraction.py'))}


def pack_candidates(hands, roi, width, height):
    landmarks = hands.multi_hand_landmarks or []
    world = hands.multi_hand_world_landmarks or []
    handedness = hands.multi_handedness or []
    n = len(landmarks)
    def xyz(points):
        if len(points.landmark) != 21:
            raise ValueError('Expected 21 hand joints')
        return np.array([[p.x,p.y,p.z] for p in points.landmark],np.float32)
    out = dict(hand_candidate_xyz=np.stack([xyz(lm) for lm in landmarks]) if n else np.empty((0,21,3),np.float32),
               hand_candidate_world_xyz=np.full((n,21,3),np.nan,np.float32),
               hand_candidate_label=np.full(n,'',dtype='<U5'),hand_candidate_score=np.full(n,np.nan,np.float32))
    for i in range(n):
        if i < len(world):out['hand_candidate_world_xyz'][i] = xyz(world[i])
        if i < len(handedness) and handedness[i].classification:
            c = handedness[i].classification[0]
            if c.label not in ('Left','Right'):raise ValueError('Unknown handedness label')
            out['hand_candidate_label'][i] = c.label
            out['hand_candidate_score'][i] = c.score
    out['hand_candidate_xyz'] = map_crop(out['hand_candidate_xyz'],roi,width,height)
    return out


def assemble(frames, source, decoder_msec, roi):
    n = len(frames)
    arrays = {k:np.concatenate([f[k] for f in frames],axis=0) for k in CANDIDATES}
    arrays.update(hand_candidate_offsets=np.r_[0,np.cumsum([len(f['hand_candidate_xyz']) for f in frames])].astype(np.int64),
                  frame_indices=source['frame_indices'][:n].copy(), timestamps=source['timestamps'][:n].copy(),
                  crop_decoder_timestamps=np.asarray(decoder_msec,np.float64)/1000., roi_xyxy=np.array(roi,np.int32))
    arrays['crop_decoder_timestamps'][~np.isfinite(arrays['crop_decoder_timestamps'])] = np.nan
    arrays['hand_candidate_finite'] = np.isfinite(arrays['hand_candidate_xyz']).all(-1)
    return arrays


def validate_candidates(a, expected_frames=None):
    keys=set(CANDIDATES)|{'hand_candidate_offsets','frame_indices','timestamps','crop_decoder_timestamps','roi_xyxy','hand_candidate_finite'}
    if set(a) != keys:raise ValueError('Unexpected candidate schema keys')
    t=len(a['frame_indices']);offsets=a['hand_candidate_offsets']
    if t<1 or (expected_frames is not None and t!=expected_frames):raise ValueError('Frame count mismatch')
    if offsets.shape!=(t+1,) or offsets.dtype!=np.int64 or offsets[0]!=0 or np.any(np.diff(offsets)<0):raise ValueError('Invalid offsets')
    d=int(offsets[-1])
    shapes={'hand_candidate_xyz':((d,21,3),np.float32),'hand_candidate_world_xyz':((d,21,3),np.float32),
            'hand_candidate_label':((d,),'<U5'),'hand_candidate_score':((d,),np.float32),
            'frame_indices':((t,),np.int32),'timestamps':((t,),np.float64),'crop_decoder_timestamps':((t,),np.float64),
            'roi_xyxy':((4,),np.int32),'hand_candidate_finite':((d,21),bool)}
    for k,(shape,dtype) in shapes.items():
        if a[k].shape!=shape or a[k].dtype!=np.dtype(dtype):raise ValueError(f'Invalid {k}')
        if a[k].dtype.kind=='f' and np.isinf(a[k]).any():raise ValueError(f'Infinite {k}')
    if not np.array_equal(a['frame_indices'],np.arange(t)):raise ValueError('Invalid frame indices')
    if not np.isfinite(a['timestamps']).all() or np.any(a['timestamps']<0) or np.any(np.diff(a['timestamps'])<=0):raise ValueError('Invalid timestamps')
    for k in ('hand_candidate_xyz','hand_candidate_world_xyz'):
        f=np.isfinite(a[k]);
        if np.any(f.any(-1)!=f.all(-1)):raise ValueError('Partially missing XYZ')
    if not np.array_equal(a['hand_candidate_finite'],np.isfinite(a['hand_candidate_xyz']).all(-1)):raise ValueError('Invalid finite mask')
    if not np.isin(a['hand_candidate_label'],['','Left','Right']).all():raise ValueError('Invalid label')
    if np.any((a['hand_candidate_score']<0)|(a['hand_candidate_score']>1)):raise ValueError('Invalid handedness score')
    x0,y0,x1,y1=a['roi_xyxy']
    if min(x0,y0)<0 or x1<=x0 or y1<=y0:raise ValueError('Invalid ROI')


def save_candidates(path, arrays, meta):
    validate_candidates(arrays)
    atomic_write(path,lambda stream:np.savez_compressed(stream,**arrays,meta_json=np.array(canonical(meta))))


def load_candidates(path):
    with np.load(path,allow_pickle=False) as f:
        a={k:f[k] for k in f.files if k!='meta_json'};m=json.loads(f['meta_json'].item())
    if m.get('schema')!=SCHEMA:raise ValueError('Not a crop candidate bank')
    validate_candidates(a)
    if m['decoded_frames']!=len(a['frame_indices']):raise ValueError('Metadata/frame count mismatch')
    return a,m


def resume_action(path, identity, source, resume):
    if not path.exists():return 'extract'
    if not resume:raise ValueError(f'Existing cache: {path}; use --resume or a new output')
    a,m=load_candidates(path)
    if m['identity']!=identity:raise ValueError(f'Mismatched cache: {path}; use a new output')
    if not np.array_equal(a['roi_xyxy'],identity['roi']):raise ValueError('Cache ROI differs from identity')
    if m['completion_status']!='complete':return 'retry_incomplete'
    validate_candidates(a,len(source['frame_indices']))
    if not np.array_equal(a['timestamps'],source['timestamps']):raise ValueError('Cache/source timestamps differ')
    verified,_=completion(m,m['official_metadata'])
    if not verified:raise ValueError('Cache claims complete but completeness checks fail')
    return 'skip'


def extract_crop(video, source, meta, policy, roi):
    import mediapipe as mp
    cap=cv2.VideoCapture(str(video));frames=[];decoder=[];sizes=set()
    try:
        if not cap.isOpened():raise ValueError(f'Cannot open video: {video}')
        reported=cap.get(cv2.CAP_PROP_FRAME_COUNT)
        reported=int(reported) if np.isfinite(reported) and reported>0 else None
        fps=cap.get(cv2.CAP_PROP_FPS);fps=float(fps) if np.isfinite(fps) and fps>0 else None
        with mp.solutions.hands.Hands(static_image_mode=policy['static_image_mode'],**policy['hands']) as detector:
            while True:
                ok,bgr=cap.read()
                if not ok:break
                if len(frames)>=len(source['frame_indices']):raise ValueError('Decoder returned extra frames')
                h,w=bgr.shape[:2];sizes.add((w,h))
                if (w,h)!=(meta['width'],meta['height']):raise ValueError('Source dimensions changed')
                decoder.append(cap.get(cv2.CAP_PROP_POS_MSEC))
                x0,y0,x1,y1=roi
                rgb=cv2.cvtColor(np.ascontiguousarray(bgr[y0:y1,x0:x1]),cv2.COLOR_BGR2RGB)
                rgb.flags.writeable=False
                frames.append(pack_candidates(detector.process(rgb),roi,w,h))
    finally:cap.release()
    if not frames:raise ValueError('No decoded frames')
    return assemble(frames,source,decoder,roi),dict(decoded_frames=len(frames),reported_frames=reported,fps=fps)



@contextmanager
def detector_log(out, record):
    """Capture native MediaPipe/OpenCV stderr per clip in each worker process."""
    path=out/'_worker_logs'/record['source_part']/(record['video_id']+'.log')
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as stream:
        stream.write(f'Extraction started {now()}\n');stream.flush()
        sys.stderr.flush();saved=os.dup(2)
        try:
            os.dup2(stream.fileno(),2)
            yield path
        finally:
            sys.stderr.flush();os.dup2(saved,2);os.close(saved)


def process_clip(job):
    record,root,out,policy,base_identity,resume=job
    row={k:record[k] for k in ('source_part','view','video_id','signer_id','gloss')}
    try:
        source,meta,video=validate_source(record,root,policy)
        roi=upper_body_crop(source,meta['width'],meta['height'],padding=policy['crop']['padding_shoulder_width'])
        identity=dict(base_identity,source_raw_sha256=record['source_raw_sha256'],source_video_sha256=record['source_video_sha256'],roi=list(roi))
        path=output_path(out,record)
        action=resume_action(path,identity,source,resume)
        if action=='skip':
            return dict(row,status='skipped_complete',decoded_frames=record['frames'],roi=list(roi))
        with detector_log(out,record):
            a,details=extract_crop(video,source,meta,policy,roi)
        complete,warnings=completion(details,meta['official_metadata'])
        status='complete' if complete else 'incomplete'
        info=dict(schema=SCHEMA,stage='detector_candidates',branch='upper_body_crop',identity=identity,
                  completion_status=status,created_utc=now(),**details,**row,
                  source_raw=record['source_raw'],source_raw_sha256=record['source_raw_sha256'],
                  source_video=record['source_video'],source_video_sha256=record['source_video_sha256'],
                  source_metadata=record['source_metadata'],metadata_sha256=record['metadata_sha256'],
                  official_metadata=meta['official_metadata'],policy=policy,roi=list(roi),width=meta['width'],height=meta['height'],
                  warnings=warnings,hand_order='detector candidate order; not anatomical sides',
                  coordinate_system='image XYZ mapped to original full image; Z scaled by crop_width/full_width; world stays hand-local',
                  timestamp_source='frame-aligned original raw timestamps',crop_uses_future_pose=True,postprocessing=[])
        save_candidates(path,a,info)
        return dict(row,status=status,**details,roi=list(roi),warnings=warnings,
                    candidates=len(a['hand_candidate_xyz']),error='' if complete else 'Decode completeness not verified')
    except Exception as exc:
        return dict(row,status='failed',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc())


def worker_init():
    # Parent owns shutdown: finish at most one in-flight clip per worker after Ctrl+C.
    signal.signal(signal.SIGINT,signal.SIG_IGN)
    cv2.setNumThreads(1)


@contextmanager
def output_lock(out):
    if fcntl is None:
        raise RuntimeError('Batch output_lock requires POSIX fcntl (macOS/Linux)')
    out.mkdir(parents=True,exist_ok=True)
    with (out/'.rescue.lock').open('a+') as stream:
        try:fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('Another rescue runner owns this output directory') from None
        try:
            stream.seek(0);stream.truncate();stream.write(str(os.getpid()));stream.flush()
            yield
        finally:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)


class StopRequest:
    def __init__(self):self.requested=False;self.previous={}
    def handle(self,*_):self.requested=True
    def __enter__(self):
        for s in (signal.SIGINT,signal.SIGTERM):
            self.previous[s]=signal.signal(s,self.handle)
        return self
    def __exit__(self,*_):
        for s,handler in self.previous.items():signal.signal(s,handler)


def schedule(jobs, pool, workers, stop, on_start, on_result):
    """Bound submissions to workers; after stop, drain in-flight work only."""
    iterator=iter(jobs);pending={};exhausted=False;announced=False
    while pending or not exhausted:
        if stop.requested and not announced:
            print('Stop requested: finishing current clips; no new clips will start.',flush=True);announced=True
        while not exhausted and not stop.requested and len(pending)<workers:
            try:job=next(iterator)
            except StopIteration:exhausted=True;break
            on_start(job)
            try:pending[pool.submit(process_clip,job)]=job
            except Exception as exc:
                stop.requested=True
                on_result(job,dict(status='failed',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc()))
        if not pending:break
        done,_=wait(pending,timeout=.25,return_when=FIRST_COMPLETED)
        for future in done:
            job=pending.pop(future)
            try:result=future.result()
            except Exception as exc:
                result=dict(status='failed',error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc())
                stop.requested=True
            on_result(job,result)


def run(args):
    root=args.project_root.resolve();selection=args.selection.resolve();policy=load_policy(args.policy)
    doc=read_selection(selection,policy);records=doc['records'][:args.max_videos] if args.max_videos else doc['records']
    out=args.output.resolve();check_output_location(out,records,root)
    # Preflight all selected sources before starting any detector or writing outputs.
    resolver=MetadataResolver()
    for i,r in enumerate(records,1):
        validate_source(r,root,policy,resolver)
        if not args.dry_run and (i%100==0 or i==len(records)):print(f'Preflight {i}/{len(records)} verified',flush=True)
    if args.dry_run:
        print(json.dumps(dict(dry_run=True,total_selection=doc['count'],selected=len(records),workers=args.workers,
              parts=dict(Counter(r['source_part'] for r in records)),signers=dict(Counter(r['signer_id'] for r in records)),
              policy_version=policy['version'],output=str(out),association=False,dedup=False),ensure_ascii=False))
        return 0
    identity=dict(selection_sha256=sha256(selection),policy=policy,code=code_identity(),runtime=runtime_info())
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS','OPENCV_FOR_THREADS_NUM'):
        os.environ[key]='1'
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid4().hex[:8]
    with output_lock(out),StopRequest() as stop:
        runs=out/'_runs'/run_id;runs.mkdir(parents=True)
        atomic_json(runs/'selection.snapshot.json',doc);atomic_json(runs/'policy.snapshot.json',policy)
        summary=dict(run_id=run_id,started_utc=now(),identity=identity,selected=len(records),total_selection=doc['count'],workers=args.workers,counts={})
        counts=Counter();finished=0;ledger=out/'manifest.csv';errors=out/'batch_errors.jsonl'
        def base(job):
            r=job[0]
            return dict(run_id=run_id,timestamp_utc=now(),schema=SCHEMA,source_path=str(project_path(root,r['source_video'])),
                source_relative_path=r['source_video'],npz_path=output_path(out,r).relative_to(out).as_posix(),
                source_sha256=r['source_video_sha256'],metadata_sha256=r['metadata_sha256'],source_metadata=r['source_metadata'],
                expected_frames=r['frames'],official_fps=r['fps'],**{k:r[k] for k in ('source_part','view','video_id','signer_id','gloss')})
        def start(job):
            manifest_row(ledger,dict(base(job),status='started'))
            r=job[0];print(f'START {r["source_part"]}/{r["video_id"]} signer={r["signer_id"]}',flush=True)
        def result(job,event):
            nonlocal finished
            finished+=1;counts[event['status']]+=1
            row=dict(base(job),**{k:v for k,v in event.items() if k not in ('warnings','traceback')},warnings=canonical(event.get('warnings',[])))
            manifest_row(ledger,row)
            error_event(runs/'events.jsonl',dict(row,roi=event.get('roi'),candidates=event.get('candidates')))
            if event['status'] in ('failed','incomplete'):error_event(errors,dict(row,traceback=event.get('traceback','')))
            summary.update(finished=finished,counts=dict(counts),updated_utc=now())
            atomic_json(runs/'run_summary.json',summary)
            print(f'[{finished}/{len(records)}] {event["status"]}: {job[0]["source_part"]}/{job[0]["video_id"]} {event.get("error","")}',flush=True)
        atomic_json(runs/'run_summary.json',summary)
        jobs=[(r,root,out,policy,identity,args.resume) for r in records]
        with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init) as pool:
            schedule(jobs,pool,args.workers,stop,start,result)
        status='interrupted' if stop.requested else 'failed' if counts['failed'] or counts['incomplete'] else 'complete'
        summary.update(status=status,finished=finished,not_started=len(records)-finished,counts=dict(counts),ended_utc=now())
        atomic_json(runs/'run_summary.json',summary)
        print(f'{status}: {dict(counts)}; not started={len(records)-finished}; summary={runs/"run_summary.json"}',flush=True)
        return 130 if stop.requested else 1 if status=='failed' else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,default=ROOT)
    sub=parser.add_subparsers(dest='command',required=True)
    plan=sub.add_parser('plan',help='Freeze approved selection with source hashes; no MediaPipe')
    plan.add_argument('--profiles',type=Path,required=True);plan.add_argument('--survey',type=Path,required=True)
    plan.add_argument('--policy',type=Path,default=DEFAULT_POLICY);plan.add_argument('--output',type=Path,default=DEFAULT_SELECTION)
    plan.add_argument('--expected-count',type=int,default=541)
    execute=sub.add_parser('run',help='Extract crop candidates only; preprocessing stays separate')
    execute.add_argument('--selection',type=Path,default=DEFAULT_SELECTION);execute.add_argument('--policy',type=Path,default=DEFAULT_POLICY)
    execute.add_argument('--output',type=Path,required=True);execute.add_argument('--workers',type=int,default=4)
    execute.add_argument('--resume',action='store_true');execute.add_argument('--dry-run',action='store_true')
    execute.add_argument('--max-videos',type=int)
    args=parser.parse_args()
    if args.command=='plan':
        doc=freeze_selection(args.profiles.resolve(),args.survey.resolve(),args.output.resolve(),load_policy(args.policy),args.project_root.resolve(),args.expected_count)
        print(json.dumps(dict(selection=str(args.output),count=doc['count'],parts=dict(Counter(r['source_part'] for r in doc['records'])),signers=dict(Counter(r['signer_id'] for r in doc['records']))),ensure_ascii=False))
        return
    if args.workers<1 or args.max_videos is not None and args.max_videos<1:parser.error('workers/max-videos must be positive')
    raise SystemExit(run(args))


if __name__=='__main__':main()
