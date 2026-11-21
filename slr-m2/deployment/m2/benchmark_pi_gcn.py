"""Measure SL-GCN 07b CPU forward latency on Raspberry Pi 4B / edge hardware (no MediaPipe)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np
import torch

from deployment.m1.common import DEFAULT_BUNDLE
from deployment.m2.classifier import BoneClassifier, deserialize_landmark_arrays


def _synthetic_landmark_arrays(num_frames: int = 60) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(42)
    xy = (rng.normal(0.0, 0.25, size=(num_frames, 50, 2))).astype(np.float32)
    # Valid shoulder anchors at slots 0 and 1 so bone adaptation never collapses.
    xy[:, 0, :] = np.array([-0.5, 0.0], dtype=np.float32)
    xy[:, 1, :] = np.array([0.5, 0.0], dtype=np.float32)
    return {
        "xy": xy,
        "usable_mask": np.ones((num_frames, 50), dtype=bool),
        "observed_mask": np.ones((num_frames, 50), dtype=bool),
        "imputed_mask": np.zeros((num_frames, 50), dtype=bool),
        "timestamps": np.linspace(0.0, 2.36, num=num_frames, dtype=np.float64),
        "frame_indices": np.arange(num_frames, dtype=np.int64),
        "association_method": np.full((num_frames, 2), "pose", dtype="<U8"),
        "normalization_fallback": np.zeros(num_frames, dtype=bool),
    }


def run_benchmark(
    *,
    bundle: Path = DEFAULT_BUNDLE,
    npz_path: Path | None = None,
    warmup: int = 2,
    runs: int = 10,
    threads: int | None = None,
    threshold_seconds: float = 1.5,
) -> dict[str, Any]:
    if threads is not None and threads > 0:
        torch.set_num_threads(threads)

    clf = BoneClassifier(bundle=bundle)
    if npz_path is not None:
        arrays = deserialize_landmark_arrays(Path(npz_path).read_bytes())
        fixture = str(Path(npz_path).resolve())
    else:
        arrays = _synthetic_landmark_arrays()
        fixture = "synthetic:60x50"

    cold_started = time.perf_counter()
    cold_res = clf.infer_from_arrays(arrays, inference_executor="pi_local")
    cold_wall = time.perf_counter() - cold_started

    for _ in range(max(0, warmup)):
        clf.infer_from_arrays(arrays, inference_executor="pi_local")

    latencies: list[float] = []
    last_res = cold_res
    for _ in range(max(1, runs)):
        last_res = clf.infer_from_arrays(arrays, inference_executor="pi_local")
        latencies.append(float(last_res["inference_seconds"]))

    arr = np.asarray(latencies, dtype=np.float64)
    p95 = float(np.percentile(arr, 95))
    passed = p95 <= float(threshold_seconds)

    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "torch_version": torch.__version__,
        "torch_num_threads": torch.get_num_threads(),
        "mediapipe_imported": "mediapipe" in sys.modules,
        "fixture": fixture,
        "source_frames": int(last_res["source_frames"]),
        "warmup_runs": max(0, warmup),
        "timed_runs": max(1, runs),
        "cold_forward_seconds": float(cold_res["inference_seconds"]),
        "cold_total_wall_seconds": float(cold_wall),
        "min_seconds": float(arr.min()),
        "median_seconds": float(np.median(arr)),
        "p95_seconds": p95,
        "max_seconds": float(arr.max()),
        "threshold_seconds": float(threshold_seconds),
        "top1_label": last_res["top1_label"],
        "top1_id": int(last_res["top1_id"]),
        "confidence": float(last_res["confidence"]),
        "verdict": "PASS" if passed else "FALLBACK_RECOMMENDED",
        "recommended_mode": "pi-split" if passed else "remote-fallback",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark SL-GCN 07b forward latency on Pi 4B / CPU")
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--npz", type=Path, default=None, help="Pre-extracted landmark .npz clip")
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=1.5)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    result = run_benchmark(
        bundle=args.bundle,
        npz_path=args.npz,
        warmup=args.warmup,
        runs=args.runs,
        threads=args.threads,
        threshold_seconds=args.threshold,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(
        f"\nVerdict: {result['verdict']} -> p95={result['p95_seconds']:.3f}s "
        f"(threshold={result['threshold_seconds']:.2f}s) | use --inference-mode {result['recommended_mode']}"
    )
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
