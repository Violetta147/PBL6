"""A6 landmark adapters for the architecture comparison."""
import numpy as np
import torch

from ablation import AblationDataset, hand_local, selected_indices
from short_gap import POLICY, repair


FRAMES = 64
CHANNELS = ('global_x', 'global_y', 'local_x', 'local_y',
            'usable', 'observed', 'imputed', 'local_valid')
STREAMS = ('joint', 'bone', 'joint_motion', 'bone_motion')
STREAM_WEIGHTS = (1.0, 0.9, 0.5, 0.5)
MODELS = ('spoter', 'sl_gcn', 'vsnet')

SL_HAND = (0, 4, 5, 8, 9, 12, 13, 16, 17, 20)
SL_NODES = (*range(8), *(8 + j for j in SL_HAND), *(29 + j for j in SL_HAND))
SL_HAND_EDGES = ((0, 1), (0, 2), (2, 3), (0, 4), (4, 5),
                 (0, 6), (6, 7), (0, 8), (8, 9))
SL_EDGES = ((0, 1), (0, 2), (2, 4), (1, 3), (3, 5), (0, 6), (1, 7),
            (4, 8), (5, 18)) + tuple(
    (u + offset, v + offset) for offset in (8, 18) for u, v in SL_HAND_EDGES
)

# feeder_wlasl_44 order, mapped from its 49-point HRNet tensor to the cache.
VS_NODES = (0, 2, 8, 10, 11, 12, 1, 3, 29, 31, 32, 33,
            *range(13, 29), *range(34, 50))


def vs_edges(arm_size, finger_size, connect_arms=False):
    """Nominal upstream skeleton at each SPD stage, in its grouped slot order."""
    edges = [(0, arm_size)] if connect_arms else []
    thumb_size = arm_size - 3
    for side in range(2):
        arm = side * arm_size
        edges.extend((j, j + 1) for j in range(arm, arm + 2 + thumb_size))
        first_finger = 2 * arm_size + side * 4 * finger_size
        for start in range(first_finger, first_finger + 4 * finger_size, finger_size):
            edges.append((arm + 2, start))
            edges.extend((j, j + 1) for j in range(start, start + finger_size - 1))
    return tuple(edges)


VS_EDGES = (vs_edges(6, 4), vs_edges(6, 3), vs_edges(4, 2, connect_arms=True))
NODE_COUNTS = {'spoter': 50, 'sl_gcn': len(SL_NODES), 'vsnet': len(VS_NODES)}


def joint_features(arrays):
    xy = np.asarray(arrays['xy'])
    usable = np.asarray(arrays['usable_mask'], dtype=bool)
    if not np.array_equal(np.isfinite(xy).all(-1), usable):
        raise ValueError('XY/usable mask mismatch')
    local = hand_local(arrays)
    x = np.zeros((*usable.shape, len(CHANNELS)), dtype=np.float32)
    x[..., :2] = np.where(usable[..., None], xy, 0.)
    x[:, 8:, 2:4] = local[:, :84].reshape(-1, 42, 2)
    x[..., 4] = usable
    x[..., 5] = arrays['observed_mask']
    x[..., 6] = arrays['imputed_mask']
    x[:, 8:, 7] = local[:, 84:]
    return x


def bone_features(joints):
    source, child = np.asarray(SL_EDGES).T
    before, after = joints[:, source], joints[:, child]
    bone = joints.copy()
    valid = (before[..., 4] != 0) & (after[..., 4] != 0)
    local_valid = (before[..., 7] != 0) & (after[..., 7] != 0)
    bone[:, child, :2] = np.where(valid[..., None], after[..., :2] - before[..., :2], 0.)
    bone[:, child, 2:4] = np.where(
        local_valid[..., None], after[..., 2:4] - before[..., 2:4], 0.)
    bone[:, child, 4] = valid
    bone[:, child, 5] = valid & (before[..., 5] != 0) & (after[..., 5] != 0)
    bone[:, child, 6] = valid & ((before[..., 6] != 0) | (after[..., 6] != 0))
    bone[:, child, 7] = local_valid
    return bone


def interval_counts(flags, left, right):
    prefix = np.vstack((np.zeros((1, flags.shape[1]), dtype=np.int64),
                        np.cumsum(flags, axis=0)))
    return prefix[right + 1] - prefix[left]


def motion_features(values, indices, mapping):
    motion = np.zeros_like(values[indices])
    left, right = indices[:-1], indices[1:]
    jumps = np.r_[0, np.cumsum(np.diff(mapping) != 1)]
    continuous = (jumps[right] == jumps[left])[:, None]
    usable = continuous & (interval_counts(values[..., 4] == 0, left, right) == 0)
    local = continuous & (interval_counts(values[..., 7] == 0, left, right) == 0)
    difference = values[right, :, :4] - values[left, :, :4]
    motion[:-1, :, :2] = np.where(usable[..., None], difference[..., :2], 0.)
    motion[:-1, :, 2:4] = np.where(local[..., None], difference[..., 2:4], 0.)
    motion[:-1, :, 4] = usable
    motion[:-1, :, 5] = usable & (interval_counts(values[..., 5] == 0, left, right) == 0)
    motion[:-1, :, 6] = usable & (interval_counts(values[..., 6] != 0, left, right) > 0)
    motion[:-1, :, 7] = local
    return motion


def adapt_clip(arrays, model, stream='joint'):
    repaired = repair(arrays)
    mapping = np.asarray(repaired['frame_indices'])
    timestamps = np.asarray(repaired['timestamps'], dtype=np.float64)
    if not len(mapping):
        raise ValueError('Empty clip')
    indices = selected_indices(len(mapping), FRAMES)
    joints = joint_features(repaired)
    if model == 'sl_gcn':
        joints = joints[:, SL_NODES]
        if stream.startswith('bone'):
            joints = bone_features(joints)
    elif model == 'vsnet':
        joints = joints[:, VS_NODES]
    sampled = (motion_features(joints, indices, mapping)
               if stream.endswith('_motion') else joints[indices])
    if stream == 'bone':
        # Match the reference bone adapter's centering over valid sampled root frames.
        root = sampled[:, 0, :2]
        valid_root = sampled[:, 0, 4].astype(bool)
        if valid_root.any():
            root[valid_root] -= root[valid_root].mean(axis=0)

    count = len(indices)
    x = np.zeros((FRAMES, NODE_COUNTS[model], len(CHANNELS)), dtype=np.float32)
    x[:count] = sampled
    real = np.arange(FRAMES) < count
    frame_indices = np.full(FRAMES, -1, dtype=np.int64)
    frame_indices[:count] = mapping[indices]
    time = np.zeros((FRAMES, 2), dtype=np.float32)
    elapsed = timestamps[indices] - timestamps[0]
    time[:count, 0] = elapsed
    time[:count, 1] = elapsed / max(timestamps[-1] - timestamps[0], 1e-8)
    imputed = repaired['imputed_mask'] & ~arrays['imputed_mask']
    if not np.isfinite(x).all():
        raise ValueError('Non-finite adapter features')
    return dict(x=torch.from_numpy(x), real=torch.from_numpy(real),
                frame_indices=torch.from_numpy(frame_indices), time=torch.from_numpy(time),
                imputed_points=torch.tensor(int(imputed.sum())))


class ArchitectureDataset(AblationDataset):
    def __init__(self, root, records, cache_sha, model, stream='joint', policy=POLICY):
        if model not in MODELS or stream not in (STREAMS if model == 'sl_gcn' else ('joint',)):
            raise ValueError(f'Unsupported model/stream: {model}/{stream}')
        if policy != POLICY or any(row['sample']['split'] not in ('train', 'val') for row in records):
            raise ValueError('Architecture training requires A6 and train/val samples')
        super().__init__(root, records, 'hand_local', cache_sha)
        self.model = model
        self.stream = stream

    def adapt_clip(self, arrays):
        return adapt_clip(arrays, self.model, self.stream)
