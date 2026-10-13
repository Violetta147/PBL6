"""Use the upstream CLI on Pi; wall timing includes loading for EACH WAV."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments'))
from common import read_csv, read_jsonl, score, sha256
from verify_results import verify
from B04.run_zipformer_pi import peak_rss_mib, sensors, speed_stats

REVISION = '5359861c739e955e79d9a303bcbc70fb988958b1'
COMMIT = 'd1be6fde11ac6e0407606b4e42fe72d34add8037'


def cli_command(binary, model, audio, output):
    return [str(binary), '-m', str(model), '-f', str(audio), '-of', str(output),
            '-l', 'vi', '-t', '2', '-p', '1', '-bo', '1', '-bs', '1',
            '-tp', '0', '-nf', '-mc', '0', '-ng', '-otxt', '-nt']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-name', required=True)
    parser.add_argument('--checkpoint', choices=['base', 'tiny'], default='base')
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()
    if Path(args.run_name).name != args.run_name or args.run_name in ['', '.', '..']:
        raise ValueError('Use one directory name')
    board = Path('/proc/device-tree/model').read_text().rstrip('\x00\n')
    if platform.machine() != 'aarch64' or 'Raspberry Pi 4' not in board:
        raise RuntimeError('Run on actual aarch64 Raspberry Pi 4')
    source = ROOT / 'whisper_cpp_v1_9_5'
    actual_commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual_commit != COMMIT:
        raise ValueError('Unexpected whisper.cpp revision')
    binary = source / 'build/bin/whisper-cli'
    model = ROOT / f'data/models/whisper_cpp/ggml-{args.checkpoint}.bin'
    manifest = ROOT / 'experiments/manifests/self_dev20.csv'
    rows = read_csv(manifest)
    if len(rows) != 20 or len({r['id'] for r in rows}) != 20:
        raise ValueError('Expected frozen self dev20')
    if args.smoke:
        rows = rows[:1]
    folder = ROOT / 'experiments/B04/results' / args.run_name
    folder.mkdir(parents=True, exist_ok=False)
    prediction = folder / 'whisper_cpp.jsonl'
    report = dict(started_utc=datetime.now(timezone.utc).isoformat(), board=board,
                  checkpoint=f'openai/whisper-{args.checkpoint} multilingual GGML',
                  runtime='whisper.cpp v1.9.5 CPU', source_commit=actual_commit,
                  model_source=f'https://huggingface.co/ggerganov/whisper.cpp/resolve/{REVISION}/{model.name}',
                  model_sha256=sha256(model), binary_sha256=sha256(binary),
                  runner_sha256=sha256(__file__), scoring_sha256=sha256(ROOT / 'experiments/common.py'),
                  manifest_sha256=sha256(manifest), smoke=args.smoke,
                  timing_scope='Per-WAV fresh CLI process wall time INCLUDES model load, WAV read and output write',
                  memory_scope='Maximum GNU time peak RSS across per-WAV CLI processes; includes model load',
                  cache_note='OS file cache may be warm; each WAV uses a new process',
                  sensors_before=sensors(), commands=[], finished=False)
    meta_path = prediction.with_suffix('.run.json')
    metadata = dict(signature=dict(manifest_sha256=sha256(manifest)), backend=report, finished=False)
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    peaks = []
    with prediction.open('w', encoding='utf-8') as output:
        for index, row in enumerate(rows, 1):
            if row['label_verified'] != 'yes' or row['split'] != 'dev':
                raise ValueError('Only verified dev input')
            audio = ROOT / row['audio_path']
            if sha256(audio) != row['audio_sha256']:
                raise ValueError('Audio hash mismatch')
            stem = folder / f'{index:02d}'
            command = cli_command(binary, model, audio, stem)
            report['commands'].append(command)
            start = time.perf_counter()
            with stem.with_suffix('.log').open('w', encoding='utf-8') as log:
                result = subprocess.run(['/usr/bin/time', '-v', '-o', str(stem.with_suffix('.time.txt')), *command],
                                        stdout=log, stderr=subprocess.STDOUT,
                                        env=dict(os.environ, LC_ALL='C'), timeout=300)
            elapsed = time.perf_counter() - start
            if result.returncode != 0 or not stem.with_suffix('.txt').exists():
                raise RuntimeError(f'CLI failed: {stem}; preserve evidence')
            text = stem.with_suffix('.txt').read_text(encoding='utf-8').strip()
            peaks.append(peak_rss_mib(stem.with_suffix('.time.txt').read_text()))
            record = dict(row, model=f'whisper_cpp_{args.checkpoint}', prediction=text, status='ok',
                          elapsed_s=elapsed, duration_s=float(row['duration_s']))
            record.update(score(row['reference'], text))
            output.write(json.dumps(record, ensure_ascii=False) + '\n')
            output.flush()
            print(f'{args.run_name} {index}/{len(rows)} wall={elapsed:.3f}s', flush=True)
    # Reuse weighted RTF math, rename inference fields to describe the actual timing.
    stats = speed_stats(read_jsonl(prediction))
    report['speed'] = {key.replace('inference_seconds', 'process_wall_seconds'): value for key, value in stats.items()}
    report.update(peak_RSS_MiB=max(peaks), sensors_after=sensors(), finished=True,
                  ended_utc=datetime.now(timezone.utc).isoformat())
    metadata.update(finished=True, backend=report)
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    if not args.smoke:
        check = verify(prediction, manifest)
        (folder / 'verification.json').write_text(json.dumps(check, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'measurement.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(**report['speed'], peak_RSS_MiB=max(peaks)), indent=2), flush=True)


if __name__ == '__main__':
    main()
