"""Diagnostic full-frame vs fixed upper-body crop pilot; never overwrites raw v3."""
import argparse
import csv
import json
from pathlib import Path
import random
import time
from types import SimpleNamespace
import cv2
import numpy as np
from extract_raw import load_raw, sha256, pack_frame
from hand_association import CANDIDATE_FIELDS


def select_rows(rows, signers, per_signer, seed):
    rng=random.Random(seed); selected=[]
    for signer in signers:
        pool=[r for r in rows if r['signer_id'].zfill(3)==signer]
        if len(pool)<per_signer: raise ValueError(f'Insufficient samples for {signer}')
        hardest=sorted(pool,key=lambda r:(-float(r['no_hand_fraction']),r['npz']))[:per_signer//2]
        ids={r['npz'] for r in hardest}
        remaining=[r for r in pool if r['npz'] not in ids]
        selected.extend([dict(r,selection='high_no_hand') for r in hardest])
        selected.extend(dict(r,selection='random') for r in rng.sample(remaining,per_signer-len(hardest)))
    return selected


def upper_body_crop(arrays, width, height, padding=.6):
    """Offline, clip-wide Pose envelope. Uses future frames; not a streaming ROI."""
    if not np.isfinite(padding) or padding < 0:
        raise ValueError('Padding must be finite and nonnegative')
    p=arrays['raw_pose_xyz'][...,:2]*[width,height]
    valid=np.isfinite(p).all(-1)&(arrays['raw_pose_visibility']>=.5)
    shoulders=np.linalg.norm(p[:,0]-p[:,1],axis=-1)
    good=valid[:,0]&valid[:,1]&(shoulders>1)
    if not good.any() or valid.sum()<2:return (0,0,width,height)
    scale=float(np.median(shoulders[good])); pts=p[valid]
    low=np.floor(pts.min(0)-padding*scale).astype(int)
    high=np.ceil(pts.max(0)+padding*scale).astype(int)
    x0,y0=np.maximum(low,[0,0]);x1,y1=np.minimum(high,[width,height])
    if x1-x0<32 or y1-y0<32:return (0,0,width,height)
    return tuple(map(int,(x0,y0,x1,y1)))


def map_crop(points, roi, width, height):
    out=points.copy();x0,y0,x1,y1=roi
    out[...,0]=(points[...,0]*(x1-x0)+x0)/width
    out[...,1]=(points[...,1]*(y1-y0)+y0)/height
    out[...,2]=points[...,2]*(x1-x0)/width
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qc-report',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--signers',nargs='+',default=['028','026','022','025','023'])
    parser.add_argument('--per-signer',type=int,default=4)
    parser.add_argument('--seed',type=int,default=42)
    args=parser.parse_args()
    if args.output.exists():parser.error('Use a new pilot output directory')
    signers=[s.zfill(3) for s in args.signers]
    if len(set(signers))!=len(signers) or args.per_signer<2:parser.error('Unique signers and per-signer >=2 required')
    with args.qc_report.open() as f:rows=select_rows(list(csv.DictReader(f)),signers,args.per_signer,args.seed)
    cfg_path=Path(__file__).with_name('raw_extraction.json');cfg=json.loads(cfg_path.read_text())
    args.output.mkdir(parents=True)
    (args.output/'selection.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    import mediapipe as mp
    from quality_control import HAND_EDGES
    report=[]
    for row in rows:
        source=Path(row['npz']);before=sha256(source);a,meta=load_raw(source)
        if meta['config']!=cfg:raise ValueError('Baseline config differs')
        video=Path(meta['source_path'])
        if sha256(video)!=meta['source_sha256']:raise ValueError('Source video changed')
        w,h=meta['width'],meta['height'];roi=upper_body_crop(a,w,h)
        key=f"{row['source_part']}_{row['video_id']}";folder=args.output/key;folder.mkdir()
        caches={mode:[] for mode in ('full','crop')};elapsed={mode:0. for mode in caches}
        preview_indices=set(np.linspace(0,len(a['frame_indices'])-1,9).astype(int).tolist());sheets=[]
        cap=cv2.VideoCapture(str(video));i=0
        try:
            with mp.solutions.hands.Hands(static_image_mode=cfg['static_image_mode'],**cfg['hands']) as full, mp.solutions.hands.Hands(static_image_mode=cfg['static_image_mode'],**cfg['hands']) as crop:
                while True:
                    ok,frame=cap.read()
                    if not ok:break
                    rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
                    x0,y0,x1,y1=roi
                    for mode,detector,img in [('full',full,rgb),('crop',crop,np.ascontiguousarray(rgb[y0:y1,x0:x1]))]:
                        start=time.perf_counter();result=detector.process(img);elapsed[mode]+=time.perf_counter()-start
                        packed=pack_frame(SimpleNamespace(pose_landmarks=None,pose_world_landmarks=None),result)
                        fields={k:packed[k] for k in CANDIDATE_FIELDS}
                        if mode=='crop':fields['hand_candidate_xyz']=map_crop(fields['hand_candidate_xyz'],roi,w,h)
                        caches[mode].append(fields)
                    if i in preview_indices:
                        pair=[]
                        for mode in caches:
                            img=frame.copy()
                            if mode=='crop':cv2.rectangle(img,(x0,y0),(x1,y1),(0,255,255),3)
                            for n,pts in enumerate(caches[mode][-1]['hand_candidate_xyz']):
                                pixels=pts[:,:2]*[w,h]
                                for u,v in HAND_EDGES:
                                    if np.isfinite(pixels[[u,v]]).all() and (np.abs(pixels[[u,v]])<10*max(w,h)).all():cv2.line(img,tuple(pixels[u].astype(int)),tuple(pixels[v].astype(int)),(0,255,0),3)
                            cv2.putText(img,f'{key} {mode} f={i} n={len(caches[mode][-1]["hand_candidate_xyz"])}',(12,30),cv2.FONT_HERSHEY_SIMPLEX,.6,(255,255,255),2)
                            pair.append(cv2.resize(img,(360,round(h*360/w))))
                        sheets.append(np.concatenate(pair,axis=1))
                    i+=1
        finally:cap.release()
        if i!=len(a['frame_indices']):raise ValueError('Pilot decode incomplete')
        metrics={}
        for mode,frames in caches.items():
            counts=np.array([len(x['hand_candidate_xyz']) for x in frames])
            fields={k:np.concatenate([x[k] for x in frames]) for k in CANDIDATE_FIELDS}
            fields['hand_candidate_offsets']=np.r_[0,np.cumsum(counts)].astype(np.int64)
            fields['frame_indices']=a['frame_indices']
            fields['meta_json']=np.array(json.dumps(dict(schema='vsl400.hand_crop_pilot.v1',mode=mode,source_npz=str(source),source_npz_sha256=before,source_video_sha256=meta['source_sha256'],config=cfg,roi=roi,coordinate_system='image XYZ mapped to full image; world remains hand-local',crop_uses_future_pose=True,code_sha256=sha256(__file__))))
            np.savez_compressed(folder/(mode+'.npz'),**fields)
            metrics[mode]=dict(no_hand_fraction=float((counts==0).mean()),one_hand_fraction=float((counts==1).mean()),overflow_fraction=float((counts>2).mean()),inference_seconds=elapsed[mode],counts=counts.tolist())
            if mode=='full':
                metrics[mode]['cached_counts_equal']=bool(np.array_equal(counts,np.diff(a['hand_candidate_offsets'])))
        if not cv2.imwrite(str(folder/'comparison.jpg'),np.concatenate(sheets,axis=0)):raise ValueError('Preview write failed')
        assert sha256(source)==before,'Raw changed'
        r=dict(signer_id=row['signer_id'],video_id=row['video_id'],part=row['source_part'],gloss=row['gloss'],selection=row['selection'],frames=i,roi=roi,metrics=metrics,raw_unchanged=True)
        report.append(r)
        (args.output/'results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print(f"{row['signer_id']} {key}: full missing={metrics['full']['no_hand_fraction']:.3f}, crop missing={metrics['crop']['no_hand_fraction']:.3f}",flush=True)
    with (args.output/'summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['signer_id','video_id','part','gloss','selection','frames','full_no_hand_fraction','crop_no_hand_fraction','delta_crop_minus_full','raw_unchanged']);writer.writeheader()
        for r in report:writer.writerow({k:r[k] for k in ['signer_id','video_id','part','gloss','selection','frames','raw_unchanged']}|dict(full_no_hand_fraction=r['metrics']['full']['no_hand_fraction'],crop_no_hand_fraction=r['metrics']['crop']['no_hand_fraction'],delta_crop_minus_full=r['metrics']['crop']['no_hand_fraction']-r['metrics']['full']['no_hand_fraction']))
    print('Diagnostic only: presence does not establish accuracy; rest/signing phases not annotated.',flush=True)

if __name__=='__main__':main()
