"""Local, memory-mapped features for the deterministic short-gap adapter."""
import hashlib
import json
from pathlib import Path
import tempfile
import time

import numpy as np
import torch
from torch.utils.data import Dataset


FIELDS = ('x', 'real', 'time', 'frame_indices', 'label', 'imputed_points')


class FeatureDataset(Dataset):
    def __init__(self, path, records):
        self.records = records
        self.arrays = {name: np.load(path / f'{name}.npy', mmap_mode='r', allow_pickle=False)
                       for name in FIELDS}
        if any(len(array) != len(records) for array in self.arrays.values()):
            raise ValueError('Feature cache count mismatch')

    def __len__(self):
        return len(self.records)

    def __getitem__(self, i):
        sample = self.records[i]['sample']
        item = {name: torch.from_numpy(np.array(values[i], copy=True))
                for name, values in self.arrays.items()}
        item['clip_id'] = '_'.join(sample[k] for k in ('source_part', 'view', 'video_id'))
        item['signer_id'] = sample['signer_id']
        return item


def materialize(source, root, split, config):
    """Publish a split only after every source record has been transformed."""
    if not len(source):
        raise ValueError('Empty feature split')
    identity = dict(format=1, split=split, records=source.records,
                    cache=config['cache_config_sha256'], adapter=config['code_hashes'],
                    policy=config['short_gap_policy'], numpy=config['numpy_version'],
                    frames=config['frames'], feature_dim=config['feature_dim'])
    digest = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    target = root / f'{split}-{digest[:16]}'
    if target.exists():
        print('Reuse features', target)
        return FeatureDataset(target, source.records)

    start = time.perf_counter()
    first = source[0]
    with tempfile.TemporaryDirectory(prefix=f'{split}-', dir=root) as scratch:
        path = Path(scratch)
        arrays = {}
        for name in FIELDS:
            value = first[name].numpy()
            arrays[name] = np.lib.format.open_memmap(
                path / f'{name}.npy', mode='w+', dtype=value.dtype,
                shape=(len(source), *value.shape))
        for i in range(len(source)):
            item = first if i == 0 else source[i]
            for name, array in arrays.items():
                array[i] = item[name].numpy()
            if (i + 1) % 1000 == 0 or i + 1 == len(source):
                print(f'Prepare {split} features {i+1}/{len(source)} '
                      f'({time.perf_counter()-start:.0f}s)', flush=True)
        for array in arrays.values():
            array.flush()
        del arrays, array
        path.rename(target)
    return FeatureDataset(target, source.records)
