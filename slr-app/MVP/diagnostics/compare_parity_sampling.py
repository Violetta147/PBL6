"""Compare fixed-crop chẵn/lẻ sampling on archived long and negative takes."""

import argparse
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desktop_mvp.check_clip import ClipRecognizer, digest, read_json, save_report
from segmentation.compare_hand_dropout import sequence_report
from segmentation.compare_timed_rest import summarize
from segmentation.sequence_splitter import (
    _top5_from_probs,
    make_slgcn_infer_fn,
    split_sign_sequence,
)

ARMS = ("baseline", "odd", "mean_even_odd")
GROUPS = ("long_sequences", "negative")


def infer_parity(arrays, infer, parity):
    frame_indices = arrays["frame_indices"]
    keep = frame_indices % 2 == parity
    if not keep.any():
        raise ValueError(f"No source frames with parity {parity}")
    sampled = {
        key: value[keep] if isinstance(value, np.ndarray) and value.ndim
        and len(value) == len(keep) else value
        for key, value in arrays.items()
    }
    return infer(sampled)


def compare_case(case, path, recognizer, infer):
    video_sha = digest(path)
    if video_sha != case["clip_sha256"]:
        raise ValueError(f"Archived video hash differs: {path.name}")
    extraction = recognizer.extract_video(path, recognizer.config)
    if (extraction.error or extraction.status not in ("success", "success_with_warning")
            or extraction.decoded_frames != case["decoded_frames"]):
        raise ValueError(f"Archived video did not decode as expected: {path.name}")
    result = split_sign_sequence(extraction.arrays, infer_fn=infer)
    baseline = sequence_report(result)
    # Timing and floating-point scores may vary; the saved decisions must match.
    saved = case["baseline"]
    if (any(baseline[key] != saved[key] for key in ("accepted", "length_limited", "labels"))
            or [list(bounds) for bounds in baseline["raw_bounds"]] != saved["raw_bounds"]
            or [s["bounds"] for s in baseline["segments"]] != [s["bounds"] for s in saved["segments"]]):
        raise ValueError(f"Could not reproduce the archived baseline: {path.name}")

    odd_segments = []
    mean_segments = []
    for segment in result["segments"]:
        arrays = segment["arrays"]
        odd = infer_parity(arrays, infer, parity=1)
        even = infer_parity(arrays, infer, parity=0)
        mean = (even["probs"] + odd["probs"]) / 2
        mean_top5 = _top5_from_probs(mean, infer.idx_to_gloss)
        odd_segments.append(dict(segment, prediction=odd, error=None))
        mean_segments.append(dict(segment, prediction={"top5": mean_top5}, error=None))
    return {
        "clip": path.name, "clip_sha256": video_sha, "fps": case["fps"],
        "group": case["group"], "expected": case["expected"], "baseline": baseline,
        "odd": sequence_report(dict(result, segments=odd_segments)),
        "mean_even_odd": sequence_report(dict(result, segments=mean_segments)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_report", type=Path)
    parser.add_argument("--camera-roll", type=Path, required=True)
    args = parser.parse_args()
    saved = read_json(args.baseline_report)
    cases = [case for case in saved["cases"] if case["group"] in GROUPS]
    if {case["group"] for case in cases} != set(GROUPS):
        parser.error("Expected both long sequences and non-signing takes")
    recognizer = ClipRecognizer()
    if saved["checkpoint_sha256"] != recognizer.checkpoint_sha:
        raise ValueError("Checkpoint differs from the archived baseline")
    infer = make_slgcn_infer_fn(recognizer, allow_training_truncation=False)
    rows = []
    for case in cases:
        folder = ROOT / "local_data" if case["capture_report_id"] else args.camera_roll
        row = compare_case(case, folder / case["clip"], recognizer, infer)
        rows.append(row)
        print(row["clip"], "expected:", row["expected"], flush=True)
        for arm in ARMS:
            print(arm, "accepted:", row[arm]["accepted"], row[arm]["labels"], flush=True)
    summary = {arm: summarize(rows, arm) for arm in ARMS}
    report = {
        "checkpoint_sha256": recognizer.checkpoint_sha,
        "reference_checks": recognizer.references, "versions": recognizer.versions,
        "baseline_report_sha256": digest(args.baseline_report),
        "summary": summary, "cases": rows,
    }
    print(summary, flush=True)
    print("Report:", save_report(report, "parity_sampling"), flush=True)


if __name__ == "__main__":
    main()
