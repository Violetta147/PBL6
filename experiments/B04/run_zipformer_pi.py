"""Measure one fresh Zipformer process on Pi; reuse the frozen ASR runner."""
import argparse
import json
import math
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments'))
from common import read_jsonl, sha256
from verify_results import verify


def speed_stats(rows):
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Need nonempty unique recordings')
    times, durations = [], []
    for row in rows:
        if row['status'] != 'ok' or row.get('elapsed_s') is None:
            raise ValueError('Incomplete inference cannot form a speed benchmark')
        elapsed, duration = float(row['elapsed_s']), float(row['duration_s'])
        if not math.isfinite(elapsed) or not math.isfinite(duration) or elapsed < 0 or duration <= 0:
            raise ValueError('Invalid inference time or audio duration')
        times.append(elapsed)
        durations.append(duration)
    rtfs = [elapsed / duration for elapsed, duration in zip(times, durations)]
    return dict(recordings=len(rows), audio_seconds=sum(durations), inference_seconds=sum(times),
                inference_seconds_median=statistics.median(times),
                inference_seconds_min=min(times), inference_seconds_max=max(times),
                RTF_total=sum(times) / sum(durations), RTF_median=statistics.median(rtfs),
                RTF_min=min(rtfs), RTF_max=max(rtfs))


def peak_rss_mib(text):
    match = re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)', text)
    if match is None:
        raise ValueError('Missing GNU time peak RSS; do not substitute zero')
    return int(match.group(1)) / 1024


def sensors():
    values = {}
    for name, args in [('temperature', ['measure_temp']), ('throttled', ['get_throttled']),
                       ('arm_clock', ['measure_clock', 'arm'])]:
        result = subprocess.run(['vcgencmd', *args], capture_output=True, text=True, timeout=5)
        values[name] = result.stdout.strip() if result.returncode == 0 else None
    return values


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-name', required=True)
    args = parser.parse_args()
    if Path(args.run_name).name != args.run_name or args.run_name in ['', '.', '..']:
        raise ValueError('Use one directory name')
    model_path = Path('/proc/device-tree/model')
    model = model_path.read_text().rstrip('\x00\n') if model_path.exists() else ''
    if platform.machine() != 'aarch64' or 'Raspberry Pi 4' not in model:
        raise RuntimeError('Run this benchmark on the actual aarch64 Raspberry Pi 4')
    folder = ROOT / 'experiments/B04/results' / args.run_name
    folder.mkdir(parents=True, exist_ok=False)
    manifest = ROOT / 'experiments/manifests/self_dev20.csv'
    prediction = folder / 'zipformer.jsonl'
    timer_log = folder / 'time.txt'
    report = dict(started_utc=datetime.now(timezone.utc).isoformat(), model=model,
                  architecture=platform.machine(), python=sys.version, platform=platform.platform(),
                  cpu_count=os.cpu_count(), manifest_sha256=sha256(manifest),
                  measurement_code_sha256=sha256(__file__), sensors_before=sensors(),
                  runtime_threads=2, cache_note='Fresh process; OS file cache may be warm after smoke/previous run',
                  timing_scope='Per-file inference excludes model loading and WAV reading',
                  memory_scope='GNU time peak RSS of full runner process, including loading/runtime')
    (folder / 'measurement.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    command = ['/usr/bin/time', '-v', '-o', str(timer_log), sys.executable,
               str(ROOT / 'experiments/run_asr.py'), '--model', 'zipformer', '--manifest', str(manifest),
               '--output', str(prediction), '--device', 'cpu', '--threads', '2']
    print(f'{args.run_name}: measure same 20 self dev WAVs on Pi, threads=2; fresh process', flush=True)
    start = time.perf_counter()
    with (folder / 'runner.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, LC_ALL='C'),
                                stdout=log, stderr=subprocess.STDOUT)
    report.update(process_wall_seconds=time.perf_counter() - start,
                  ended_utc=datetime.now(timezone.utc).isoformat(),
                  sensors_after=sensors(), process_exit_code=result.returncode)
    (folder / 'measurement.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if result.returncode != 0:
        raise RuntimeError(f'Runner failed; preserve evidence in {folder}')
    check = verify(prediction, manifest)
    if check['total'] != 20 or check['completed'] != 20:
        raise ValueError('Expected 20 completed recordings; preserve partial evidence')
    report.update(speed=speed_stats(read_jsonl(prediction)),
                  peak_RSS_MiB=peak_rss_mib(timer_log.read_text()),
                  model_load_seconds=json.loads(prediction.with_suffix('.run.json').read_text())['load_seconds'])
    (folder / 'verification.json').write_text(json.dumps(check, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder / 'measurement.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(run=args.run_name, **report['speed'], peak_RSS_MiB=report['peak_RSS_MiB'],
                          model_load_seconds=report['model_load_seconds'], WER_ws=check['WER_ws'], CER=check['CER']), indent=2), flush=True)


if __name__ == '__main__':
    main()
