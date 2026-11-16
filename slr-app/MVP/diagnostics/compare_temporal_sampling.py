"""Compare 25 FPS sampling with unchanged inputs on saved kiosk segments."""

import argparse
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desktop_mvp.check_clip import ADAPTER, ClipRecognizer, digest, read_json, save_report
from segmentation.boundary_detector import slice_feature_arrays
from segmentation.sequence_splitter import make_slgcn_infer_fn

TARGET_FPS = 25


def source_rows(count, fps):
    if not math.isfinite(fps) or fps <= 0 or count <= 0:
        raise ValueError("Sampling requires frames and a positive capture FPS")
    if fps <= TARGET_FPS:
        return np.arange(count)
    # The recordings store mean measured FPS, so infer uniform source times.
    # Anchor at crop start and stop the target grid at the last source sample.
    last_target = math.floor((count - 1) * TARGET_FPS / fps)
    return np.floor(np.arange(last_target + 1) * fps / TARGET_FPS + 0.5).astype(int)


def sample_arrays(arrays, fps):
    count = len(arrays["upper_body"])
    rows = source_rows(count, fps)
    if len(rows) == count:
        return arrays
    return {
        key: value[rows] if isinstance(value, np.ndarray) and value.ndim
        and len(value) == count else value
        for key, value in arrays.items()
    }


def verify_native(recognizer, infer):
    from prepare_clip import read_features

    results = []
    for reference in recognizer.references:
        video_id = reference["video_id"]
        arrays = read_features(ADAPTER / "reference/training_qc" / f"{video_id}_front.npz")
        sampled = sample_arrays(arrays, TARGET_FPS)
        baseline, _ = recognizer.prepare_arrays(arrays)
        candidate, _ = recognizer.prepare_arrays(sampled)
        if not np.array_equal(baseline, candidate) or infer(arrays)["top5"] != infer(sampled)["top5"]:
            raise ValueError(f"25 FPS identity check failed for {video_id}")
        results.append(video_id)
    return results


def compare_case(recognizer, infer, case, truth):
    path = ROOT / "local_data" / case["clip"]
    if digest(path) != case["clip_sha256"]:
        raise ValueError(f"Video hash differs: {path.name}")
    baseline_segments = case["baseline"]["segments"]
    if not case["baseline"]["accepted"] or len(baseline_segments) != len(truth):
        raise ValueError(f"Expected accepted segments aligned to labels: {path.name}")
    extraction = recognizer.extract_video(path, recognizer.config)
    if extraction.error or extraction.decoded_frames != case["decoded_frames"]:
        raise ValueError(f"Unable to reproduce extraction for {path.name}: {extraction.error}")
    fps = case["observed_fps"]
    segments = []
    for segment, label in zip(baseline_segments, truth, strict=True):
        start, end = segment["bounds"]
        arrays = slice_feature_arrays(extraction.arrays, start, end)
        baseline = infer(arrays)["top5"]
        if [p["index"] for p in baseline] != [p["index"] for p in segment["top5"]]:
            raise ValueError(f"Saved baseline Top-5 differs: {path.name}, [{start}, {end})")
        sampled = sample_arrays(arrays, fps)
        candidate = infer(sampled)["top5"]
        segments.append({
            "bounds": [start, end], "expected": label, "original_frames": end - start,
            "retained_frame_indices": sampled["frame_indices"].tolist(),
            "baseline": baseline, "sampled_25_fps": candidate,
        })
    result = {"clip": path.name, "clip_sha256": case["clip_sha256"],
              "observed_fps": fps, "expected": truth, "segments": segments}
    for arm in ("baseline", "sampled_25_fps"):
        result[arm] = [segment[arm][0]["gloss"] for segment in segments]
    print(path.name, f"{fps:.2f} FPS", result["baseline"], "->", result["sampled_25_fps"], flush=True)
    return result


def summarize(cases, arm):
    return {
        "exact_sequences": sum(case[arm] == case["expected"] for case in cases),
        "total_sequences": len(cases),
        "correct_positions": sum(
            predicted == expected
            for case in cases for predicted, expected in zip(case[arm], case["expected"], strict=True)
        ),
        "total_positions": sum(len(case["expected"]) for case in cases),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_report", type=Path)
    parser.add_argument("score_report", type=Path)
    args = parser.parse_args()
    saved = read_json(args.baseline_report)
    scored = read_json(args.score_report)
    if scored["sequence_source"] != args.baseline_report.name:
        raise ValueError("Score report does not reference the baseline")
    truth = {row["clip"]: row["expected"] for row in scored["sequence_rows"]}
    recognizer = ClipRecognizer()
    if saved["checkpoint_sha256"] != recognizer.checkpoint_sha:
        raise ValueError("Expected the baseline checkpoint")
    infer = make_slgcn_infer_fn(recognizer)
    native = verify_native(recognizer, infer)
    cases = [compare_case(recognizer, infer, case, truth[case["clip"]]) for case in saved["cases"]
             if case["clip"] in truth]
    if not cases or {case["clip"] for case in cases} != truth.keys():
        raise ValueError("Missing baseline clips")
    summary = {arm: summarize(cases, arm) for arm in ("baseline", "sampled_25_fps")}
    report = {
        "target_fps": TARGET_FPS, "time_source": "mean observed capture FPS",
        "checkpoint_sha256": recognizer.checkpoint_sha, "versions": recognizer.versions,
        "baseline_report_sha256": digest(args.baseline_report),
        "score_report_sha256": digest(args.score_report),
        "native_identical_tensor_and_top5": native, "summary": summary, "cases": cases,
    }
    print(summary, flush=True)
    print("Report:", save_report(report, "temporal_sampling_25fps"), flush=True)


if __name__ == "__main__":
    main()
