"""PBL6 candidate v3: 2D geometry adapter, not an SL-GCN model.

Heuristic wrist gate is a train-QC proposal, not from the official paper.
Source coordinates stay in raw_joints; rejected coordinates remain missing.
"""
import numpy as np

HAND_IDX = [0, 4, 5, 8, 9, 12, 13, 16, 17, 20]
WRIST_PAIRS = ((5, 7), (6, 17))


def wrist_distance(x):
    return np.stack([np.linalg.norm(x[:, a] - x[:, b], axis=-1)
                     for a, b in WRIST_PAIRS], axis=1)


def quality_repair(raw, detection, handedness, repair_array, wrist_threshold=1.0):
    raw = np.asarray(raw, dtype=np.float32)
    T = len(raw)
    assert T > 0 and raw.shape == (T, 27, 2) and not np.isinf(raw).any()
    assert detection.shape == (T, 4) and handedness.shape == (T, 2)
    assert np.isin(detection, [0, 1]).all() and np.isin(handedness, [0, 1]).all()
    assert wrist_threshold > 0
    source_observed = np.isfinite(raw).all(-1)
    # Pairwise atomic coordinates: partial x/y is an unresolved schema issue.
    assert np.array_equal(np.isfinite(raw).any(-1), source_observed), 'Partial x/y joint; audit required.'
    det, hv = detection.astype(bool), handedness.astype(bool)
    raw_distance = wrist_distance(raw)
    geometry_pre = np.any(np.isfinite(raw_distance) & (raw_distance > wrist_threshold), axis=1)
    geometry_block = geometry_pre.copy()
    blocked = np.broadcast_to(geometry_block[:, None], (T, 27)).copy()
    mask_rejected = np.zeros((T, 27), dtype=bool)
    body_conflict = source_observed[:, :7].any(1) & ~det[:, 0]
    mask_rejected[body_conflict, :7] = True
    for side, (lo, hi) in enumerate(((7, 17), (17, 27))):
        allowed = det[:, 0] & det[:, 2 + side] & hv[:, side]
        conflict = source_observed[:, lo:hi].any(1) & ~allowed
        mask_rejected[conflict, lo:hi] = True
    # Recompute from the original observations after any new quarantine.
    # Each new pass rejects >=1 extra frame, so at most T+1 passes can occur.
    for repair_pass in range(T + 1):
        blocked = mask_rejected | geometry_block[:, None]
        gated = raw.copy()
        gated[blocked] = np.nan
        repaired = gated.copy()
        warnings = []
        # A quality-rejected frame is a barrier, including after rechecking repair.
        for lo, hi, name in ((0, 7, 'body'), (7, 17, 'left'), (17, 27, 'right')):
            allowed_frames = ~blocked[:, lo:hi].any(1)
            changes = np.diff(np.r_[False, allowed_frames, False].astype(np.int8))
            for start, end in zip(np.flatnonzero(changes == 1), np.flatnonzero(changes == -1)):
                fixed, msgs = repair_array(gated[start:end, lo:hi].copy(), name, 5, 'nan', 10)
                repaired[start:end, lo:hi] = fixed
                warnings.extend([f'{name}: source segment [{start},{end}): {s}' for s in msgs])
        post_distance = wrist_distance(repaired)
        newly_blocked = np.any(np.isfinite(post_distance) & (post_distance > wrist_threshold), axis=1)
        if not newly_blocked.any():
            break
        assert not np.any(newly_blocked & geometry_block)
        geometry_block |= newly_blocked
    else:
        raise AssertionError('Quality repair did not reach a stable mask.')
    observed = source_observed & ~blocked
    available = np.isfinite(repaired).all(-1)
    assert np.array_equal(repaired[observed], raw[observed])
    assert not available[blocked].any(), 'Repair filled a quality-rejected joint.'
    return dict(joints=repaired, source_observed=source_observed,
                observed=observed, available=available, imputed=available & ~observed,
                quality_blocked=blocked, mask_rejected=mask_rejected,
                geometry_blocked=geometry_block, geometry_blocked_pre=geometry_pre,
                geometry_blocked_post=geometry_block & ~geometry_pre,
                raw_wrist_distance=raw_distance,
                repaired_wrist_distance=wrist_distance(repaired), warnings=warnings)


def build_from_raw(raw, detection, handedness, frame_indices, timestamps,
                   repair_array, edges, wrist_threshold=1.0):
    T = len(raw)
    out = quality_repair(raw, detection, handedness, repair_array, wrist_threshold)
    index = np.arange(150) % T if T < 150 else np.arange(150)
    result = {k: v[index] for k, v in out.items() if isinstance(v, np.ndarray)}
    result.update(raw_joints=raw[index].astype(np.float32), source_indices=index.astype(np.int64),
                  detection_masks=detection[index], handedness_valid=handedness[index],
                  frame_indices=frame_indices[index], timestamps=timestamps[index],
                  frames_original=T, warnings=out['warnings'],
                  missing_before_pct=float(100 * (1-out['observed'].mean())),
                  missing_after_pct=float(100 * (1-out['available'].mean())))
    joints, valid = result['joints'], result['available']
    bone, bone_valid = np.full_like(joints, np.nan), np.zeros((150, 27), dtype=bool)
    bone[:, 0], bone_valid[:, 0] = joints[:, 0], valid[:, 0]
    for parent, child in edges:
        good = valid[:, parent] & valid[:, child]
        bone[good, child] = joints[good, child] - joints[good, parent]
        bone_valid[:, child] = good
    result['bone'] = np.where(bone_valid[..., None], bone, 0).transpose(2, 0, 1)[..., None].astype(np.float32)
    result['bone_valid'] = bone_valid
    assert np.isfinite(result['bone']).all()
    return result


def convert(z, repair_array, edges, wrist_threshold=1.0):
    hands = []
    for side_i, side in enumerate(('left', 'right')):
        common = z[f'{side}_hand_local'] * z['hand_scales'][:, side_i, None, None] + z[f'{side}_palm_body'][:, 0:1]
        hands.append(common[:, HAND_IDX])
    raw = np.concatenate([z['upper_body'], *hands], axis=1).astype(np.float32)
    return build_from_raw(raw, z['detection_masks'], z['handedness_valid'], z['frame_indices'],
                          z['timestamps'], repair_array, edges, wrist_threshold)


def prepare_input(bone, bone_valid, start=0, length=150):
    assert bone.shape == (2, 150, 27, 1) and bone_valid.shape == (150, 27)
    assert 0 <= start and length > 0 and start + length <= 150
    x = bone[:, start:start + length].copy()
    root, good = x[:, :, 0, 0], bone_valid[start:start + length, 0]
    if good.any():
        root[:, good] -= root[:, good].mean(axis=1, keepdims=True)
    root[:, ~good] = 0
    assert np.isfinite(x).all()
    return x
