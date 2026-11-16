"""Offline comparison of one short-gap merge per archived kiosk sequence."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desktop_mvp.check_clip import ClipRecognizer, digest, read_json, save_report
from segmentation.boundary_detector import slice_feature_arrays
from segmentation.compare_hand_dropout import sequence_report
from segmentation.compare_timed_rest import summarize
from segmentation.sequence_splitter import SequenceSplitConfig, make_slgcn_infer_fn, split_sign_sequence

MAX_GAP_MS = 750
ARM = "short_gap_merge"


def sole_pair(baseline, fps, max_frames):
    """Find one pair of consecutive raw intervals that both survived filtering."""
    if baseline["length_limited"]:
        return None
    eligible = {}
    for index, (raw_start, raw_end) in enumerate(baseline["raw_bounds"]):
        for segment_index, segment in enumerate(baseline["segments"]):
            start, end = segment["bounds"]
            if start <= raw_start < raw_end <= end and segment["top5"] and not segment["error"]:
                eligible[index] = segment_index
    pairs = []
    for index, (left, right) in enumerate(zip(baseline["raw_bounds"], baseline["raw_bounds"][1:])):
        gap_ms = (right[0] - left[1]) * 1000 / fps
        if index not in eligible or index + 1 not in eligible or not 0 <= gap_ms <= MAX_GAP_MS:
            continue
        first, second = eligible[index], eligible[index + 1]
        start = baseline["segments"][first]["bounds"][0]
        end = baseline["segments"][second]["bounds"][1]
        if second == first + 1 and end - start <= max_frames:
            pairs.append((index, first, start, end, gap_ms))
    return pairs[0] if len(pairs) == 1 else None


def run_merge(case, pair, path, recognizer, infer, config):
    if digest(path) != case["clip_sha256"]:
        raise ValueError(f"Video hash differs: {path.name}")
    extracted = recognizer.extract_video(path, recognizer.config)
    if (extracted.error or extracted.status not in ("success", "success_with_warning")
            or extracted.decoded_frames != case["decoded_frames"]):
        raise ValueError(f"Could not reproduce extraction: {path.name}")
    result = split_sign_sequence(extracted.arrays, cfg=config, infer_fn=infer)
    baseline = sequence_report(result)
    saved = case["baseline"]
    if ([list(bound) for bound in baseline["raw_bounds"]] != saved["raw_bounds"]
            or any(baseline[key] != saved[key] for key in ("accepted", "length_limited", "labels"))
            or [s["bounds"] for s in baseline["segments"]] != [s["bounds"] for s in saved["segments"]]):
        raise ValueError(f"Baseline differs from archive: {path.name}")

    raw_index, first, start, end, _ = pair
    left, right = result["raw_segment_bounds"][raw_index:raw_index + 2]
    prediction = infer(slice_feature_arrays(extracted.arrays, start, end))
    segments = result["segments"]
    merged = dict(segments[first], t_start=start, t_end=end, prediction=prediction)
    raw = result["raw_segment_bounds"]
    return sequence_report(dict(result,
                                segments=segments[:first] + [merged] + segments[first + 2:],
                                raw_segment_bounds=raw[:raw_index] + [(left[0], right[1])]
                                + raw[raw_index + 2:]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("additional_archive", type=Path)
    parser.add_argument("scores", type=Path)
    parser.add_argument("--camera-roll", type=Path, required=True)
    args = parser.parse_args()
    archive = read_json(args.archive)
    other = read_json(args.additional_archive)
    scored = read_json(args.scores)
    if scored["sequence_source"] != args.additional_archive.name:
        parser.error("Scores must refer to the additional archive")
    truth = {row["clip"]: row["expected"] for row in scored["sequence_rows"]}
    if truth.keys() != {case["clip"] for case in other["cases"]}:
        parser.error("Need confirmed labels for every additional clip")
    cases = archive["cases"] + [dict(case, fps=case["observed_fps"], expected=truth[case["clip"]])
                                for case in other["cases"]]
    config = SequenceSplitConfig()
    recognizer = ClipRecognizer()
    if any(source["checkpoint_sha256"] != recognizer.checkpoint_sha for source in (archive, other)):
        raise ValueError("Checkpoint differs from archive")
    infer = make_slgcn_infer_fn(recognizer, allow_training_truncation=False)
    rows = []
    for case in cases:
        fps = case["fps"]
        candidate = case["baseline"]
        pair = sole_pair(candidate, fps, config.max_segment_frames)
        if pair is not None:
            folder = ROOT / "local_data" if case["capture_report_id"] else args.camera_roll
            candidate = run_merge(case, pair, folder / case["clip"], recognizer, infer, config)
        rows.append({"clip": case["clip"], "clip_sha256": case["clip_sha256"], "fps": fps,
                     "expected": case["expected"], "baseline": case["baseline"],
                     "merged_bounds": list(pair[2:4]) if pair else None,
                     "gap_ms": pair[4] if pair else None, ARM: candidate})
        if pair is not None:
            print(case["clip"], "gap ms:", round(pair[4], 3), "bounds:", pair[2:4],
                  "baseline:", case["baseline"]["labels"], "merged:", candidate["labels"], flush=True)
    summary = {arm: summarize(rows, arm) for arm in ("baseline", ARM)}
    report = {"max_gap_ms": MAX_GAP_MS, "checkpoint_sha256": recognizer.checkpoint_sha,
              "reference_checks": recognizer.references,
              "report_hashes": {p.name: digest(p) for p in (args.archive, args.additional_archive, args.scores)},
              "summary": summary, "cases": rows}
    print(summary, flush=True)
    print("Report:", save_report(report, "short_gap_merge"), flush=True)


if __name__ == "__main__":
    main()
