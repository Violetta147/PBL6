"""Repair short gaps in normalized hand XY before A1 sampling."""
import numpy as np
import torch

from ablation import AblationDataset, adapt

POLICY = {
    'version': 'hand_xy_short_gap_v1',
    'max_missing_seconds': 0.08,
}


def _possible_swap(xy, usable, methods, left, right):
    wrists = [8, 29]
    if not usable[[left, right]][:, wrists].all():
        return False
    if not (methods[[left, right]] == 'pose').all():
        return False
    before, after = xy[[left, right]][:, wrists]
    direct = np.linalg.norm(before - after, axis=1).sum()
    crossed = np.linalg.norm(before - after[::-1], axis=1).sum()
    return crossed < direct


def repair(arrays, policy=POLICY):
    if policy != POLICY:
        raise ValueError('Unsupported short-gap policy')
    xy = np.asarray(arrays['xy'])
    usable = np.asarray(arrays['usable_mask'], dtype=bool)
    observed = np.asarray(arrays['observed_mask'], dtype=bool)
    imputed = np.asarray(arrays['imputed_mask'], dtype=bool)
    times = np.asarray(arrays['timestamps'], dtype=np.float64)
    indices = np.asarray(arrays['frame_indices'])
    methods = np.asarray(arrays['association_method'])
    fallback = np.asarray(arrays['normalization_fallback'], dtype=bool)
    if not np.isfinite(times).all() or (np.diff(times) <= 0).any():
        raise ValueError('Invalid timestamps for short-gap repair')

    repaired_xy = xy.copy()
    repaired_usable = usable.copy()
    repaired_imputed = imputed.copy()
    for joint in range(8, 50):
        side = (joint - 8) // 21
        anchors = np.flatnonzero(usable[:, joint])
        for k in np.flatnonzero(np.diff(anchors) > 1):
            left, right = anchors[k:k + 2]
            gap = slice(left + 1, right)
            window = slice(left, right + 1)
            # Count the missing interval from both sides for irregular timestamps.
            missing_seconds = max(times[right] - times[left + 1], times[right - 1] - times[left])
            if missing_seconds > policy['max_missing_seconds'] + 1e-9:
                continue
            if (observed[gap, joint].any() or imputed[window, joint].any()
                    or fallback[window].any() or (np.diff(indices[window]) != 1).any()):
                continue
            if methods[left, side] != 'pose' or methods[right, side] != 'pose':
                continue
            if (methods[window] == 'ambiguous').any() or _possible_swap(xy, usable, methods, left, right):
                continue
            fraction = (times[gap] - times[left]) / (times[right] - times[left])
            repaired_xy[gap, joint] = xy[left, joint] + fraction[:, None] * (xy[right, joint] - xy[left, joint])
            repaired_usable[gap, joint] = True
            repaired_imputed[gap, joint] = True

    return dict(arrays, xy=repaired_xy, usable_mask=repaired_usable, imputed_mask=repaired_imputed)


class ShortGapDataset(AblationDataset):
    def __init__(self, root, records, config_sha256, policy=POLICY):
        super().__init__(root, records, 'hand_local', config_sha256)
        if policy != POLICY:
            raise ValueError('Unsupported short-gap policy')
        self.policy = policy

    def adapt_clip(self, arrays):
        repaired = repair(arrays, self.policy)
        item = adapt(repaired, 'hand_local')
        item['imputed_points'] = torch.tensor(int((repaired['imputed_mask'] & ~arrays['imputed_mask']).sum()))
        return item
