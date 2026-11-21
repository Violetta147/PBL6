"""Train and compare VSL400 architectures using only the frozen train/val cache."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import platform
from pathlib import Path
import re

import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader

from architecture_data import (
    ArchitectureDataset, CHANNELS, FRAMES, MODELS, NODE_COUNTS, SL_EDGES, SL_NODES,
    STREAMS, STREAM_WEIGHTS, VS_EDGES, VS_NODES,
)
from architecture_models import build_model
import architecture_runner
import feature_cache
import io_utils
import runner
from short_gap import POLICY


CACHE_ID = 'b0_v3_1d5c730b092b6aa7'
CACHE_SHA = '1d5c730b092b6aa782ed68e2a8305cdc890676b2ef8711041e3a1282284b2c69'
REFERENCE_ID = '20261111T090251683576Z'
REFERENCE_HASHES = {
    'config.json': '5b8cc6d6fdd09f145bf985f17528b4f9640e0a3009e3f85cefa9fbac72d679da',
    'validation.json': 'd2818e5b46d7af42de102cb06cb0b56220fff3d9c1cd7caec9301b15a690e708',
    'label_map.json': '1e21de38231acabfd12bbdb167c396209e9893d9767d4161ab6d6a439a01d0f0',
    'validation_predictions.jsonl': 'e2c5fea4a71ec1c80d093dd806202ec402b8073dab37df8118013ce46d7eba5e',
}
SOURCES = {
    'spoter': ('maty-bohacek/spoter', '0f909bf92690772f43f0062be41860ed85b461ad'),
    'sl_gcn': ('jackyjsy/CVPR21Chal-SLR', 'de6c53a6fbbc08a5d9a728e33614a4541836714c'),
    'vsnet': ('atinyboy/VSNet', '8b5be23de3917a032b2611f10900c0a1f50ca850'),
}
RECIPE = dict(batch_size=64, lr=.0003, weight_decay=.01, epochs=40, patience=10,
              grad_clip=1., num_workers=0, optimizer='AdamW', scheduler='cosine',
              accumulation_steps=1)
MODEL_RECIPES = {
    'spoter': dict(batch_size=32, accumulation_steps=4, lr=1e-4, weight_decay=1e-4,
                   epochs=50, patience=7, scheduler='plateau', scheduler_factor=.5,
                   scheduler_patience=2),
    'sl_gcn': dict(batch_size=16, lr=.01, weight_decay=1e-4, epochs=60, patience=60,
                   optimizer='SGD', momentum=.9, nesterov=True, scheduler='multistep',
                   milestones=[30, 45], scheduler_factor=.1),
    'vsnet': {},
}
VARIANTS = {
    'spoter': 'iteration_v1_learned_frame_positions_a6',
    'sl_gcn': 'vsl400_bone_reference_recipe_a6',
    'vsnet': 'vsformer_temporal_windows_a6',
}
ADAPTER_FILES = ('dataset.py', 'ablation.py', 'short_gap.py', 'architecture_data.py',
                 'feature_cache.py')


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + '\n').encode()


def digest_json(value):
    return hashlib.sha256(json_bytes(value)).hexdigest()


def write_bytes(path, content):
    temp = path.with_name(path.name + '.partial')
    temp.write_bytes(content)
    temp.replace(path)


def write_json(path, value):
    write_bytes(path, json_bytes(value))


def read_json(path):
    return json.loads(path.read_text())


def read_predictions(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def write_predictions(path, predictions):
    lines = (json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n'
             for record in predictions)
    write_bytes(path, ''.join(lines).encode())


def metadata(row):
    sample = row['sample']
    return dict(clip_id='_'.join(sample[k] for k in ('source_part', 'view', 'video_id')),
                signer_id=sample['signer_id'], target=row['label_id'])


def membership(records):
    result = {r['clip_id']: (r['signer_id'], r['target']) for r in records}
    if len(result) != len(records):
        raise ValueError('Duplicate clip ID')
    return result


def require_membership(actual, expected):
    if membership(actual) != membership(expected):
        raise ValueError('Validation clip IDs, signer IDs or targets differ')


def prediction_metrics(predictions, classes):
    targets, guesses, signers = (
        [r[key] for r in predictions] for key in ('target', 'prediction', 'signer_id'))
    if not predictions or any(not 0 <= x < classes for x in targets + guesses):
        raise ValueError('Invalid validation predictions')
    result = runner.metrics(targets, guesses, signers, classes)
    result['signer_support'] = dict(sorted(Counter(signers).items()))
    return result


def load_protocol(cloud, work, local_cache):
    source = cloud / 'training/ablations/A6_hand_local_short_gap' / REFERENCE_ID
    if not (source / '_SUCCESS').is_file():
        raise ValueError('Incomplete A6 reference')
    ref_dir = work / 'reference' / REFERENCE_ID
    for name, sha in REFERENCE_HASHES.items():
        io_utils.stage(source / name, ref_dir / name, sha)
    reference = dict(config=read_json(ref_dir / 'config.json'),
                     metrics=read_json(ref_dir / 'validation.json'),
                     predictions=read_predictions(ref_dir / 'validation_predictions.jsonl'))
    ref_config = reference['config']
    if (ref_config['cache_id'], ref_config['cache_config_sha256'], ref_config['short_gap_policy'],
            ref_config['frames'], ref_config['ablation'], ref_config['seed']) != (
            CACHE_ID, CACHE_SHA, POLICY, FRAMES, 'hand_local_short_gap', 42):
        raise ValueError('Unexpected A6 reference configuration')
    _, records, labels = io_utils.stage_cache(
        cloud / 'preprocessing/caches' / CACHE_ID, local_cache, CACHE_SHA)
    if ({k: len(v) for k, v in records.items()} != {'train': 17325, 'val': 3711}
            or len({row['shard'] for rows in records.values() for row in rows}) != 42
            or len(labels) != 400 or labels != read_json(ref_dir / 'label_map.json')):
        raise ValueError('Unexpected VSL400 split, shards or label map')
    require_membership(reference['predictions'], [metadata(row) for row in records['val']])
    recalculated = prediction_metrics(reference['predictions'], len(labels))
    for key, value in recalculated.items():
        if key == 'signer_support':
            continue
        recorded = reference['metrics'][key]
        matches = (math.isclose(recorded, value, abs_tol=1e-12)
                   if isinstance(value, float) else recorded == value)
        if not matches:
            raise ValueError(f'A6 reference metric does not match its predictions: {key}')
    reference['metrics'].update(recalculated)
    return records, labels, reference


def environment(device):
    runtime = dict(torch_version=str(torch.__version__), numpy_version=np.__version__,
                   python_version=platform.python_version(), device=str(device))
    if device.type == 'cuda':
        runtime.update(gpu=torch.cuda.get_device_name(device), cuda_version=torch.version.cuda,
                       cudnn_version=torch.backends.cudnn.version())
    return runtime


def make_config(model, seed, batch_size, device, code_dir, records, reference):
    if model not in MODELS or type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('Choose one MODEL and a uint32 SEED')
    if batch_size not in (None, 8, 16, 32, 64):
        raise ValueError('BATCH_SIZE must be None, 8, 16, 32 or 64')
    recipe = RECIPE | MODEL_RECIPES[model]
    if batch_size is not None:
        recipe['batch_size'] = batch_size
    runtime = environment(device)
    ref_config = reference['config']
    graph = {'spoter': None,
             'sl_gcn': dict(cache_nodes=SL_NODES, inward_edges=SL_EDGES, keep_probability=.9),
             'vsnet': dict(cache_nodes=VS_NODES, inward_edges_by_stage=VS_EDGES,
                           groups_before_drop=(6, 6, 8, 8, 8, 8), window=(8, 4),
                           keep_probability=.9)}[model]
    effective_batch = recipe['batch_size'] * recipe['accumulation_steps']
    baseline_recipe = RECIPE | ref_config | {'effective_batch_size': ref_config['batch_size']}
    compared_recipe = recipe | {'seed': seed, 'effective_batch_size': effective_batch}
    differences = {k: dict(reference=baseline_recipe.get(k), current=value)
                   for k, value in compared_recipe.items() if baseline_recipe.get(k) != value}
    return dict(schema='vsl400.architecture_comparison.v2', model=model, seed=seed,
                model_variant=VARIANTS[model], effective_batch_size=effective_batch,
                classes=400, frames=FRAMES, feature_dim=NODE_COUNTS[model] * len(CHANNELS),
                feature_shape=[FRAMES, NODE_COUNTS[model], len(CHANNELS)],
                feature_channels=CHANNELS, graph=graph, precision='fp32',
                sampling='uniform_unique_then_right_padding_v1', augmentation=False,
                selection_metric='validation_macro_f1',
                bone_root_centering=model == 'sl_gcn',
                padding_policy='real_mask_in_temporal_ops_and_pooling',
                graph_degree_normalization='absolute_column_sum_floor_1' if graph else None,
                cache_id=CACHE_ID, cache_config_sha256=CACHE_SHA, short_gap_policy=POLICY,
                membership_sha256=digest_json(records), reference_run=REFERENCE_ID,
                reference_hashes=REFERENCE_HASHES, upstream_repo=SOURCES[model][0],
                upstream_commit=SOURCES[model][1],
                code_hashes={p.name: io_utils.sha(p) for p in sorted(code_dir.glob('*.py'))},
                recipe_differences=differences,
                environment_differences={k: dict(reference=ref_config.get(k), current=v)
                                         for k, v in runtime.items() if ref_config.get(k) != v},
                **recipe, **runtime)


def build_run_path(cloud, model, resume):
    if resume is not None and not re.fullmatch(r'\d{8}T\d{12}Z', resume):
        raise ValueError('Invalid RESUME_RUN_ID')
    run_id = resume or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    return cloud / 'training/architecture_comparison' / model / run_id


def assert_config(path, config):
    if path.exists() and path.read_bytes() != json_bytes(config):
        raise ValueError(f'Resume config differs: {path}. Start a new run.')


def mark_success(directory):
    files = sorted(p for p in directory.rglob('*') if p.is_file()
                   and not p.name.endswith('.partial')
                   and (p.parent != directory or p.name not in ('_SUCCESS', 'SHA256SUMS')))
    checksums = ''.join(f'{io_utils.sha(p)}  {p.relative_to(directory).as_posix()}\n'
                        for p in files)
    write_bytes(directory / 'SHA256SUMS', checksums.encode())
    write_bytes(directory / '_SUCCESS', (io_utils.sha(directory / 'SHA256SUMS') + '\n').encode())


def verify_success(directory):
    manifest = directory / 'SHA256SUMS'
    if io_utils.sha(manifest) != (directory / '_SUCCESS').read_text().strip():
        raise ValueError(f'Completion manifest mismatch: {directory}')
    for line in manifest.read_text().splitlines():
        sha, name = line.split(maxsplit=1)
        if io_utils.sha(io_utils.safe(directory, name)) != sha:
            raise ValueError(f'Completed artifact checksum mismatch: {directory / name}')


def materialized_loader(cache, records, features, config, stream, split):
    source = ArchitectureDataset(cache, records, CACHE_SHA, config['model'], stream,
                                 config['short_gap_policy'])
    feature_config = config | {'code_hashes': {k: config['code_hashes'][k] for k in ADAPTER_FILES}}
    try:
        dataset = feature_cache.materialize(source, features / config['model'] / stream,
                                            split, feature_config)
    finally:
        source.close()
    training = split == 'train'
    generator = torch.Generator().manual_seed(config['seed']) if training else None
    return DataLoader(dataset, batch_size=config['batch_size'], shuffle=training,
                      generator=generator, num_workers=config['num_workers'])


def check_batch(model, batch, device, config):
    model.to(device).train()
    optimizer = architecture_runner.make_optimizer(model, config)
    x, real, time, target = (batch[k].to(device) for k in ('x', 'real', 'time', 'label'))
    scores = model(x, real, time)
    if scores.shape != (len(target), config['classes']) or not scores.isfinite().all():
        raise ValueError('Invalid preflight logits')
    loss = F.cross_entropy(scores, target)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), config['grad_clip'], error_if_nonfinite=True)
    optimizer.step()


def frame_order_delta(model, batch, device):
    """Reverse valid feature frames while keeping their time slots fixed."""
    x, real, time = (batch[k][:1].to(device) for k in ('x', 'real', 'time'))
    reversed_x = x.clone()
    reversed_x[real] = x[real].flip(0)
    model.eval()
    with torch.inference_mode():
        original = model(x, real, time)
        reversed_logits = model(reversed_x, real, time)
    return (original - reversed_logits).abs().max().item()


def preflight(cache, records, config, device):
    runner.seed_all(config['seed'])
    if device.type == 'cuda':
        torch.cuda.reset_peak_memory_stats(device)
    streams = STREAMS if config['model'] == 'sl_gcn' else ('joint',)
    # Prefer long clips, since padding cannot make an OOM check easier.
    count = config['batch_size']
    rows = sorted(records['train'], key=lambda row: -row['frames'])[:count]
    order_delta = None
    for stream in streams:
        source = ArchitectureDataset(cache, rows, CACHE_SHA, config['model'], stream)
        try:
            batch = next(iter(DataLoader(source, batch_size=count)))
            model = build_model(config['model'], config['classes'])
            check_batch(model, batch, device, config)
            if config['model'] in ('spoter', 'vsnet'):
                order_delta = frame_order_delta(model, batch, device)
                if not math.isfinite(order_delta) or order_delta <= 1e-5:
                    raise ValueError(f'Logits did not respond to reversed frames: {order_delta}')
                print(f'Reversed frame order changed logits (max delta {order_delta:.4g})')
            print(f'Preflight OK: {config["model"]}/{stream}, batch {len(batch["x"])}',
                  flush=True)
            del model, batch
        finally:
            source.close()
    if device.type == 'cuda':
        peak = torch.cuda.max_memory_allocated(device) / 1024**3
        print(f'Peak CUDA allocation during preflight: {peak:.2f} GiB')
    else:
        peak = None
    return dict(batch_size=count, streams=list(streams), peak_cuda_gib=peak,
                frame_order_logit_delta=order_delta)


def export_stream_scores(model, loader, device, path):
    model.eval()
    scores, records = [], []
    with torch.inference_mode():
        for batch in loader:
            x, real, time = (batch[k].to(device) for k in ('x', 'real', 'time'))
            logits = model(x, real, time).cpu()
            if not logits.isfinite().all():
                raise ValueError('Non-finite validation scores')
            scores.append(logits.numpy())
            records.extend(dict(clip_id=cid, signer_id=signer, target=target)
                           for cid, signer, target in zip(batch['clip_id'], batch['signer_id'],
                                                          batch['label'].tolist()))
    temp = path.with_name(path.name + '.partial')
    with temp.open('wb') as handle:
        np.save(handle, np.concatenate(scores), allow_pickle=False)
    temp.replace(path)
    write_predictions(path.with_suffix('.jsonl'), records)


def assemble_ensemble(run, expected, classes):
    order = {r['clip_id']: i for i, r in enumerate(expected)}
    combined = np.zeros((len(expected), classes), dtype=np.float64)
    manifest, histories = {}, {}
    for stream, weight in zip(STREAMS, STREAM_WEIGHTS):
        directory = run / stream
        verify_success(directory)
        rows = read_predictions(directory / 'validation_logits.jsonl')
        require_membership(rows, expected)
        logits = np.load(directory / 'validation_logits.npy', allow_pickle=False)
        if logits.shape != combined.shape or not np.isfinite(logits).all():
            raise ValueError(f'Invalid score tensor: {stream}')
        indices = [order[row['clip_id']] for row in rows]
        combined[indices] += weight * logits.astype(np.float64)
        checkpoint = directory / 'best.pt'
        config = read_json(directory / 'config.json')
        manifest[stream] = dict(checkpoint=checkpoint.relative_to(run).as_posix(),
                                sha256=io_utils.sha(checkpoint), weight=weight,
                                best_epoch=read_json(directory / 'validation.json')['best_epoch'],
                                parameters=config['parameters'])
        histories[stream] = read_json(directory / 'history.json')
    combined /= sum(STREAM_WEIGHTS)
    predictions = [dict(r, prediction=int(p)) for r, p in zip(expected, combined.argmax(1))]
    metrics = prediction_metrics(predictions, classes)
    targets = torch.tensor([r['target'] for r in expected])
    metrics['loss'] = F.cross_entropy(torch.from_numpy(combined), targets).item()
    metrics['best_epoch_by_stream'] = {s: info['best_epoch'] for s, info in manifest.items()}
    write_predictions(run / 'validation_predictions.jsonl', predictions)
    write_json(run / 'validation.json', metrics)
    write_json(run / 'history.json', histories)
    write_json(run / 'ensemble.json', dict(
        streams=manifest, reduction='weighted_mean_logits',
        parameters=sum(info['parameters'] for info in manifest.values())))
    return metrics, predictions


def fit_stream(config, directory, loaders, device, export_logits):
    runner.seed_all(config['seed'])
    model = build_model(config['model'], config['classes'])
    train, val = loaders
    architecture_runner.fit(model, train, val, config, directory, device)
    last = runner.load_checkpoint(directory / 'last.pt')
    write_json(directory / 'history.json', last['history'])
    predictions = read_predictions(directory / 'validation_predictions.jsonl')
    metrics = read_json(directory / 'validation.json')
    metrics['signer_support'] = dict(sorted(Counter(r['signer_id'] for r in predictions).items()))
    write_json(directory / 'validation.json', metrics)
    if export_logits:
        export_stream_scores(model, val, device, directory / 'validation_logits.npy')
        mark_success(directory)
    return metrics, predictions


def comparison(config, metrics, predictions, reference, joint=None, bone=None):
    require_membership(predictions, reference['predictions'])
    baseline = reference['metrics']
    if metrics['class_support'] != baseline['class_support']:
        raise ValueError('Validation class support differs')
    keys = ('top1', 'macro_f1', 'macro_signer_top1', 'worst_signer_top1')

    def delta(base, value):
        return dict(reference=base, candidate=value, delta_pp=100 * (value - base))

    return dict(model=config['model'], seed=config['seed'], frames=config['frames'],
                model_variant=config['model_variant'],
                reference_run=config['reference_run'], reference_best_epoch=baseline['best_epoch'],
                parameters=config['parameters'], reference_parameters=reference['config']['parameters'],
                recipe_differences=config['recipe_differences'],
                environment_differences=config['environment_differences'],
                training_lots=len(STREAMS) if joint is not None else 1,
                best_epoch=metrics.get('best_epoch'),
                best_epoch_by_stream=metrics.get('best_epoch_by_stream'),
                validation={k: delta(baseline[k], metrics[k]) for k in keys},
                signers={s: dict(clips=metrics['signer_support'][s],
                                 **delta(baseline['signer_top1'][s], score))
                         for s, score in metrics['signer_top1'].items()},
                joint_stream_validation={k: joint[k] for k in (*keys, 'best_epoch')}
                if joint is not None else None,
                bone_stream_validation={k: bone[k] for k in (*keys, 'best_epoch')}
                if bone is not None else None,
                interpretation='Validation comparison of architecture, adapter and training recipe')


def run_comparison(run, config, records, labels, reference, local_cache, features, code_dir,
                   device, resume=False, preflight_result=None):
    expected = [metadata(row) for row in records['val']]
    require_membership(expected, reference['predictions'])
    ensemble = config['model'] == 'sl_gcn'
    runner.seed_all(config['seed'])
    parameters = sum(p.numel() for p in build_model(config['model'], config['classes']).parameters())
    config = config | {'parameters': parameters * (len(STREAMS) if ensemble else 1)}
    if ensemble:
        config.update(streams=list(STREAMS), stream_weights=list(STREAM_WEIGHTS),
                      parameters_per_stream=parameters)

    if resume:
        if not (run / 'config.json').is_file():
            raise ValueError(f'Resume run not found: {run}')
        assert_config(run / 'config.json', config)
        if (run / '_SUCCESS').exists():
            verify_success(run)
            return read_json(run / 'comparison.json')
    else:
        run.mkdir(parents=True, exist_ok=False)
    write_json(run / 'config.json', config)
    write_json(run / 'label_map.json', labels)
    if preflight_result is not None and not (run / 'preflight.json').exists():
        write_json(run / 'preflight.json', preflight_result)
    for name, digest in config['code_hashes'].items():
        io_utils.stage(code_dir / name, run / 'code' / name, digest)

    streams = STREAMS if ensemble else ('joint',)
    for stream in streams:
        directory = run / stream if ensemble else run
        if ensemble and (directory / '_SUCCESS').exists():
            verify_success(directory)
            continue
        stream_config = config | {'stream': stream, 'parameters': parameters} if ensemble else config
        loaders = [materialized_loader(local_cache, records[split], features, config, stream, split)
                   for split in ('train', 'val')]
        metrics, predictions = fit_stream(stream_config, directory, loaders, device, ensemble)
        require_membership(predictions, expected)
        del loaders
    joint = bone = None
    if ensemble:
        metrics, predictions = assemble_ensemble(run, expected, config['classes'])
        joint = read_json(run / 'joint' / 'validation.json')
        bone = read_json(run / 'bone' / 'validation.json')
    report = comparison(config, metrics, predictions, reference, joint, bone)
    write_json(run / 'comparison.json', report)
    mark_success(run)
    return report
