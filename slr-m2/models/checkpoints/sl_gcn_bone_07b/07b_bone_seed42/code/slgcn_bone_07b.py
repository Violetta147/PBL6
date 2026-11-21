"""A6 bone features with the legacy repeat, truncate and crop policy."""
import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset

import architecture_comparison as experiment
from architecture_data import ArchitectureDataset, SL_NODES, bone_features, joint_features
from architecture_models import build_model
import feature_cache
import io_utils
import runner
from short_gap import repair

CACHE_FRAMES = 150
TRAIN_FRAMES = 100


class BoneSequenceDataset(ArchitectureDataset):
    def adapt_clip(self, arrays):
        repaired = repair(arrays)
        joints = joint_features(repaired)[:, SL_NODES]
        if not len(joints):
            raise ValueError('Empty landmark sequence')
        indices = np.arange(CACHE_FRAMES) % len(joints)
        return dict(x=torch.from_numpy(bone_features(joints)[indices]),
                    real=torch.ones(CACHE_FRAMES, dtype=torch.bool),
                    time=torch.zeros((CACHE_FRAMES, 2), dtype=torch.float32),
                    frame_indices=torch.from_numpy(arrays['frame_indices'][indices]),
                    imputed_points=torch.tensor(int(
                        (repaired['imputed_mask'] & ~arrays['imputed_mask']).sum())))


class BoneWindowDataset(Dataset):
    def __init__(self, source, training):
        self.source = source
        self.training = training

    def __len__(self):
        return len(self.source)

    def __getitem__(self, index):
        item = self.source[index]
        if self.training:
            start = int(torch.randint(CACHE_FRAMES - TRAIN_FRAMES + 1, ()))
            for name in ('x', 'real', 'time', 'frame_indices'):
                item[name] = item[name][start:start + TRAIN_FRAMES]
        # The feature cache returns a fresh tensor for each access.
        root = item['x'][:, 0, :2]
        valid = item['x'][:, 0, 4].bool()
        if valid.any():
            root[valid] -= root[valid].mean(dim=0)
        return item


def make_loader(cache, rows, features, config, split):
    source = BoneSequenceDataset(cache, rows, experiment.CACHE_SHA, 'sl_gcn', 'bone')
    try:
        adapter_files = (*experiment.ADAPTER_FILES, 'slgcn_bone_07b.py')
        feature_config = config | {
            'code_hashes': {name: config['code_hashes'][name] for name in adapter_files}}
        dataset = feature_cache.materialize(source, features, split, feature_config)
    finally:
        source.close()
    training = split == 'train'
    generator = torch.Generator().manual_seed(config['seed']) if training else None
    return DataLoader(BoneWindowDataset(dataset, training), batch_size=config['batch_size'],
                      shuffle=training, generator=generator, num_workers=0)


def run_bone(run, seed, records, labels, reference, cache, features, code_dir, device):
    config = experiment.make_config('sl_gcn', seed, None, device, code_dir, records, reference)
    differences = config['recipe_differences']
    differences['grad_clip'] = dict(reference=reference['config']['grad_clip'], current=None)
    config.update(model_variant='slgcn_bone_07b_revamped_100_150',
                  stream='bone', frames=CACHE_FRAMES, train_frames=TRAIN_FRAMES,
                  feature_shape=[CACHE_FRAMES, len(SL_NODES), len(config['feature_channels'])],
                  sampling='repeat_or_first_150_then_random_train_crop',
                  padding_policy='all_positions_real_including_repeats',
                  selection_metric='validation_top1_then_loss', grad_clip=None,
                  parameters=sum(p.numel() for p in build_model('sl_gcn').parameters()))
    run.mkdir(parents=True, exist_ok=True)
    experiment.assert_config(run / 'config.json', config)
    if (run / '_SUCCESS').exists():
        experiment.verify_success(run)
        return experiment.read_json(run / 'comparison.json')
    experiment.write_json(run / 'config.json', config)
    experiment.write_json(run / 'label_map.json', labels)
    for name, digest in config['code_hashes'].items():
        io_utils.stage(code_dir / name, run / 'code' / name, digest)
    loaders = [make_loader(cache, records[s], features, config, s) for s in ('train', 'val')]
    metrics, predictions = experiment.fit_stream(config, run, loaders, device, False)
    report = experiment.comparison(config, metrics, predictions, reference, bone=metrics)
    experiment.write_json(run / 'comparison.json', report)
    experiment.mark_success(run)
    return report
