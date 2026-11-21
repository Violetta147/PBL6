"""NumPy-only preprocessing pilot; raw files are never modified."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import numpy as np
import hand_association
import pair_guard

from hand_association import CANDIDATE_FIELDS, associate_sequence

FUSION_POLICY = dict(version='geometry_alias_pilot_v1', max_distance=.35,
                     ambiguity_margin=.08, representative='full')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def relative_path(root, name):
    p = PurePosixPath(name)
    require(not p.is_absolute() and '..' not in p.parts and bool(p.parts), f'Unsafe path: {name}')
    target = Path(root).joinpath(*p.parts)
    require(target.resolve().is_relative_to(Path(root).resolve()), f'Path escapes root: {name}')
    return target


def checksum_map(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        require(len(digest) == 64 and name not in result, 'Bad checksum list')
        relative_path(Path(path).parent, name)
        result[name] = digest
    return result


def copy_verified(source, target, digest):
    source, target = Path(source), Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and sha(target) == digest:
        return target
    tmp = target.with_suffix(target.suffix + '.partial')
    shutil.copyfile(source, tmp)
    require(sha(tmp) == digest, f'Checksum mismatch: {source}')
    tmp.replace(target)
    return target


def unpack_verified(archive, root):
    """Call only after archive verification; reject links/devices and traversal."""
    with tarfile.open(archive) as tar:
        seen = set()
        for member in tar:
            target = relative_path(root, member.name)
            require(member.name not in seen and member.isfile(), f'Unsafe tar member: {member.name}')
            seen.add(member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as src, target.open('wb') as dst:
                shutil.copyfileobj(src, dst)


def key(row):
    return (row['source_part'], row['view'], row['video_id'])


def select_pilot(rows, per_group=8, extra_keys=()):
    """Deterministic signer round-robin in each split × crop group; no test."""
    chosen = {}
    for split in ('train', 'val'):
        for crop in (False, True):
            group = sorted((r for r in rows if r['split'] == split and bool(r['crop']) == crop), key=key)
            signers = sorted({r['signer_id'] for r in group})
            queues = {s: [r for r in group if r['signer_id'] == s] for s in signers}
            count = 0
            while count < per_group and any(queues.values()):
                for s in signers:
                    if queues[s] and count < per_group:
                        r = queues[s].pop(0); chosen[key(r)] = r; count += 1
    lookup = {key(r): r for r in rows}
    for k in extra_keys:
        k = tuple(k)
        require(k in lookup and lookup[k]['split'] in ('train', 'val'), f'Invalid extra key: {k}')
        chosen[k] = lookup[k]
    return sorted(chosen.values(), key=lambda r: (r['split'], *key(r)))


def load_bank(root, entry, frames, schema):
    path = relative_path(root, entry['path'])
    require(entry['schema'] == schema and sha(path) == entry['sha256'], f'Invalid input: {path}')
    with np.load(path, allow_pickle=False) as z:
        meta = json.loads(z['meta_json'].item())
        a = {k: z[k] for k in z.files if k != 'meta_json'}
    require(meta['schema'] == schema, 'Wrong schema')
    require(frames > 0 and a['frame_indices'].shape == (frames,), 'Frame count mismatch')
    require(np.array_equal(a['frame_indices'], np.arange(frames)), 'Unexpected frame mapping')
    t = a['timestamps']
    require(t.shape == (frames,) and np.isfinite(t).all() and (t >= 0).all() and (np.diff(t) > 0).all(), 'Bad timestamps')
    offsets = a['hand_candidate_offsets']
    require(offsets.shape == (frames+1,) and offsets.dtype.kind in 'iu' and offsets[0] == 0 and (np.diff(offsets) >= 0).all(), 'Bad offsets')
    n = int(offsets[-1])
    for k, shape in zip(CANDIDATE_FIELDS, ((n,21,3), (n,21,3), (n,), (n,))):
        require(a[k].shape == shape, f'Bad shape: {k}')
    require(np.isfinite([meta['width'], meta['height']]).all() and min(meta['width'], meta['height']) > 0, 'Bad dimensions')
    if schema == 'vsl400.detector_raw.v3':
        require(a['raw_pose_xyz'].shape == (frames,8,3) and a['raw_pose_visibility'].shape == (frames,8), 'Bad Pose8')
        require(meta.get('pose_indices', [11,12,13,14,15,16,23,24]) == [11,12,13,14,15,16,23,24], 'Bad topology')
    return a, meta


def load_sample(root, row):
    full, meta = load_bank(root, row['full'], row['frames'], 'vsl400.detector_raw.v3')
    require(meta['source_sha256'] == row['source_video_sha256'], 'Wrong source video')
    crop = None
    if row['crop']:
        crop, cm = load_bank(root, row['crop'], row['frames'], 'vsl400.crop_candidates.v1')
        require(np.array_equal(full['timestamps'], crop['timestamps']), 'Full/crop time mismatch')
        require((cm['width'], cm['height']) == (meta['width'], meta['height']), 'Dimension mismatch')
        require('mapped to original full image' in cm.get('coordinate_system', ''), 'Crop coordinates not in full-image system')
    return full, crop, meta


def frame_at(a, i):
    start, end = a['hand_candidate_offsets'][i:i+2]
    return {k: a[k][start:end] for k in CANDIDATE_FIELDS}


def fuse_frame(full, crop, aspect, policy):
    """Conservative cross-source geometry aliasing, no within-source removal.

    Pilot heuristic only: temporal validation is left to association and review.
    Ambiguous matches retain both candidates, which may make association abstain.
    """
    a = full['hand_candidate_xyz'][...,:2] * [1, aspect]
    b = crop['hand_candidate_xyz'][...,:2] * [1, aspect]
    costs = np.full((len(a), len(b)), np.inf)
    for i, p in enumerate(a):
        for j, q in enumerate(b):
            scale = np.mean([np.median(np.linalg.norm(x[[5,9,13,17]]-x[0], axis=-1)) for x in (p,q)])
            if not np.isfinite(p).all() or not np.isfinite(q).all() or not np.isfinite(scale) or scale < 1e-6:
                continue
            cost = max(np.linalg.norm(p-q, axis=-1).mean(), np.linalg.norm(p[0]-q[0])) / scale
            if cost <= policy['max_distance']:
                costs[i,j] = cost
    pairs = {}; uncertain = 0
    for i in range(len(a)):
        if not len(b) or not np.isfinite(costs[i]).any():
            continue
        j = int(np.argmin(costs[i])); best = costs[i,j]
        if np.argmin(costs[:,j]) != i:
            continue
        alt = np.r_[np.delete(costs[i], j), np.delete(costs[:,j], i)]
        if len(alt) and alt.min()-best < policy['ambiguity_margin']:
            uncertain += 1
        else:
            pairs[j] = i
    unmatched = [j for j in range(len(b)) if j not in pairs]
    out = {k: np.concatenate([full[k], crop[k][unmatched]]) for k in CANDIDATE_FIELDS}
    fi = np.r_[np.arange(len(a)), np.full(len(unmatched), -1)].astype(np.int32)
    ci = np.full(len(fi), -1, np.int32)
    for j,i in pairs.items():
        ci[i] = j
    ci[len(a):] = unmatched
    out.update(fusion_full_indices=fi, fusion_crop_indices=ci)
    return out, uncertain


def fuse_sequence(full, crop, aspect, policy):
    frames = []; ambiguous = []
    for i in range(len(full['frame_indices'])):
        f = frame_at(full, i)
        empty = {k: v[:0] for k,v in f.items()}
        out, n = fuse_frame(f, frame_at(crop,i) if crop is not None else empty, aspect, policy)
        frames.append(out); ambiguous.append(n)
    fields = (*CANDIDATE_FIELDS, 'fusion_full_indices', 'fusion_crop_indices')
    out = {k: np.concatenate([f[k] for f in frames]) for k in fields}
    out['hand_candidate_offsets'] = np.r_[0, np.cumsum([len(f['hand_candidate_xyz']) for f in frames])].astype(np.int64)
    out['fusion_ambiguous_matches'] = np.array(ambiguous, np.int32)
    return out


def normalize(full, associated, aspect, visibility_min=.5):
    """Offline clip-median scale; fallback center is clip median of valid centers.

    With no trustworthy shoulders, leave normalized output missing (no unit guess).
    """
    pose = full['raw_pose_xyz'][...,:2] * [1,aspect]
    hands = associated['associated_hand_xyz'][...,:2] * [1,aspect]
    xy = np.concatenate([pose, hands.reshape(len(pose),42,2)], axis=1)
    observed = np.isfinite(xy).all(-1)
    pose_valid = np.isfinite(full['raw_pose_visibility']) & (full['raw_pose_visibility'] >= visibility_min)
    valid = observed.copy(); valid[:,:8] &= pose_valid
    center = pose[:,:2].mean(axis=1)
    widths = np.linalg.norm(pose[:,0]-pose[:,1], axis=-1)
    anchor_ok = valid[:,:2].all(-1) & np.isfinite(widths) & (widths > 1e-6)
    fallback = ~anchor_ok
    norm = np.full(xy.shape, np.nan, np.float32)
    scale = np.nan
    if anchor_ok.any():
        scale = float(np.median(widths[anchor_ok]))
        center[fallback] = np.median(center[anchor_ok], axis=0)
        norm = ((xy-center[:,None,:])/scale).astype(np.float32)
    else:
        center[:] = np.nan
    normalized_valid = valid & np.isfinite(norm).all(-1)
    norm[~normalized_valid] = np.nan
    return dict(xy=norm, observed_mask=observed, usable_mask=normalized_valid,
                imputed_mask=np.zeros_like(observed), padding_mask=np.zeros(len(pose), bool),
                normalization_anchor_valid=anchor_ok, normalization_fallback=fallback,
                normalization_center=center, normalization_scale=np.array(scale))


def longest_gap_seconds(missing, timestamps, fps):
    dt = np.diff(timestamps)
    tail = 1/fps if np.isfinite(fps) and fps > 0 else (float(np.median(dt)) if len(dt) else 0.)
    durations = np.r_[dt, tail]
    best = current = 0.
    for flag, duration in zip(missing, durations):
        current = current + float(duration) if flag else 0.
        best = max(best, current)
    return best


def process(full, crop, meta, association_policy, fusion_policy=FUSION_POLICY, pair_guard_policy=None):
    aspect = meta['height']/meta['width']
    fused = fuse_sequence(full, crop, aspect, fusion_policy)
    association_input = dict(fused, raw_pose_xyz=full['raw_pose_xyz'], raw_pose_visibility=full['raw_pose_visibility'])
    if pair_guard_policy is None:
        assoc = associate_sequence(association_input, association_policy, aspect)
    else:
        evidence = pair_guard.detect_sequence(fused, full['timestamps'], aspect, pair_guard_policy)
        assoc = pair_guard.associate_sequence(hand_association, association_input, association_policy, aspect, evidence)
        fused.update(evidence)
    norm = normalize(full, assoc, aspect, association_policy['pose_visibility_min'])
    chosen_full = np.full(assoc['association_indices'].shape, -1, np.int32)
    chosen_crop = chosen_full.copy()
    for i, indices in enumerate(assoc['association_indices']):
        for side, idx in enumerate(indices):
            if idx >= 0:
                flat = fused['hand_candidate_offsets'][i] + idx
                chosen_full[i,side] = fused['fusion_full_indices'][flat]
                chosen_crop[i,side] = fused['fusion_crop_indices'][flat]
    out = dict(fused, **assoc, **norm, selected_full_indices=chosen_full, selected_crop_indices=chosen_crop,
               frame_indices=full['frame_indices'], timestamps=full['timestamps'])
    assigned = assoc['association_indices'] >= 0
    wrists = assoc['associated_hand_xyz'][:,:,0,:2] * [1,aspect]
    jump = np.linalg.norm(np.diff(wrists, axis=0), axis=-1)
    qc = dict(frames=len(assigned), candidates_input=int(full['hand_candidate_offsets'][-1] + (crop['hand_candidate_offsets'][-1] if crop is not None else 0)),
              candidates_retained=int(fused['hand_candidate_offsets'][-1]), assigned_sides=int(assigned.sum()),
              ambiguous_sides=int((assoc['association_method']=='ambiguous').sum()),
              dedup_ambiguous_frames=int((fused['fusion_ambiguous_matches']>0).sum()),
              anchor_fallback_frames=int(norm['normalization_fallback'].sum()),
              normalized_usable_fraction=float(norm['usable_mask'].mean()),
              wrist_jump_suspects=int((jump > .15).sum()),
              missing_side_max_seconds=[longest_gap_seconds(~assigned[:,s], full['timestamps'], meta['fps']) for s in range(2)])
    if pair_guard_policy is not None:
        qc.update(duplicate_pair_suspects=int(len(evidence['duplicate_pair_indices'])),
                  duplicate_pairs_blocked=int(evidence['duplicate_pair_blocked'].sum()),
                  duplicate_pair_frames=int(sum(bool(pair_guard.conflicts_at(evidence,t)) for t in range(len(full['timestamps'])))))
    return out, qc
