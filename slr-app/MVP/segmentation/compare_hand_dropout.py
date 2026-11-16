"""Compare pose-assisted continuation against the kiosk on saved webcam clips."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desktop_mvp.check_clip import ClipRecognizer, digest
from segmentation.boundary_detector import compute_kinematic_signals, slice_feature_arrays
from segmentation.compare_timed_rest import SCARF, THANKS, cases, summarize
from segmentation.sequence_splitter import SequenceSplitConfig, make_slgcn_infer_fn, split_sign_sequence

MAX_DROPOUT_SECONDS = 1.8
MOTION_ONSET_SECONDS = 0.25
KIOSK_CASES = (
    ("20261115T194512_307491Z", [SCARF, THANKS, "Rửa mặt"]),
    ("20261115T194703_761752Z", [SCARF, THANKS, SCARF, THANKS]),
    ("20261115T194105_650797Z", []),
    ("20261115T200731_161984Z", [SCARF, THANKS, SCARF, THANKS]),
)


def continue_with_pose(signals, fps, minimum_detected_run):
    """Extend established activity only during missing-hand frames with pose support."""
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("Expected a positive observed capture FPS")
    active = signals["active_raw"]
    extended = active.copy()
    eligible = ~signals["hand_present"] & signals["wrist_in_active_zone"]
    max_frames = max(1, round(MAX_DROPOUT_SECONDS * fps))
    onset_frames = max(1, round(MOTION_ONSET_SECONDS * fps))
    edges = np.flatnonzero(np.diff(np.r_[False, active, False]))
    for start, end in zip(edges[::2], edges[1::2], strict=True):
        if end - start < minimum_detected_run:
            continue
        window_end = min(len(active), end + max_frames)
        stops = np.flatnonzero(~eligible[end:window_end])
        stop = end + int(stops[0]) if stops.size else window_end
        onset_end = min(stop, end + onset_frames)
        if signals["motion_above_thresh"][end:onset_end].any():
            extended[end:stop] = True
    return extended


def evaluation_clips(camera_roll):
    for path, _, expected, _ in cases(camera_roll):
        if expected is not None and len(expected) != 1:
            group = "two_signs" if expected else "negative"
            yield path, group, expected, None, None
    for report_id, expected in KIOSK_CASES:
        path = ROOT / "outputs" / "desktop_demo" / report_id / "report.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        capture = report["capture"]
        group = "long_sequences" if expected else "negative"
        yield ROOT / "local_data" / Path(report["video"]).name, group, expected, capture, report_id


def sequence_report(result):
    segments = [
        {"bounds": [segment["t_start"], segment["t_end"]],
         "top5": segment["prediction"]["top5"] if segment["prediction"] else [],
         "error": segment["error"]}
        for segment in result["segments"]
    ]
    raw = result["raw_segment_bounds"]
    accepted = (len(raw) >= 2 and len(raw) == len(segments) and not result["length_limited"]
                and all(s["top5"] and s["error"] is None for s in segments))
    return {"accepted": accepted, "raw_bounds": raw, "segments": segments,
            "length_limited": result["length_limited"],
            "labels": [s["top5"][0]["gloss"] if s["top5"] else None for s in segments]}


def recover_one_short_segment(arrays, baseline, added, cfg, infer):
    """Try only one unambiguous short rejection without changing accepted crops."""
    raw = baseline["raw_bounds"]
    kept = baseline["segments"]
    if (len(raw) < 2 or len(raw) != len(kept) + 1 or baseline["length_limited"]
            or any(s["error"] is not None or not s["top5"] for s in kept)):
        return baseline

    total = len(added)
    short = [(s, e) for s, e in raw if min(total, e + cfg.margin_frames)
             - max(0, s - cfg.margin_frames) < cfg.min_segment_frames]
    if len(short) != 1:
        return baseline
    raw_start, raw_end = short[0]
    first_unadded = np.flatnonzero(~added[raw_end:])
    supported_end = raw_end + int(first_unadded[0]) if first_unadded.size else total
    if supported_end == raw_end:
        return baseline

    before = [s for s in kept if s["bounds"][0] < raw_start]
    after = kept[len(before):]
    left_limit = before[-1]["bounds"][1] if before else 0
    right_limit = after[0]["bounds"][0] if after else total
    recovered_end = min(supported_end, right_limit)
    start = max(left_limit, raw_start - cfg.margin_frames)
    end = min(right_limit, recovered_end + cfg.margin_frames)
    if recovered_end <= raw_end or not cfg.min_segment_frames <= end - start <= cfg.max_segment_frames:
        return baseline

    try:
        prediction = infer(slice_feature_arrays(arrays, start, end))
    except ValueError as exc:
        return {**baseline, "recovery_error": str(exc)}
    recovered = {"bounds": [start, end], "top5": prediction["top5"], "error": None}
    segments = [*before, recovered, *after]
    raw_bounds = [(s, recovered_end if (s, e) == short[0] else e) for s, e in raw]
    return {**baseline, "accepted": True, "raw_bounds": raw_bounds, "segments": segments,
            "labels": [s["top5"][0]["gloss"] for s in segments]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera-roll", required=True, type=Path)
    args = parser.parse_args()
    inputs = list(evaluation_clips(args.camera_roll))
    for path, *_ in inputs:
        if not path.is_file():
            parser.error(f"Missing evaluation clip: {path}")

    print("Comparing complete ordered sequences, segment counts and false acceptances.", flush=True)
    config = SequenceSplitConfig()
    rec = ClipRecognizer()
    infer = make_slgcn_infer_fn(rec, allow_training_truncation=False)
    rows = []
    for path, group, expected, capture, report_id in inputs:
        extracted = rec.extract_video(path, rec.config)
        if extracted.error or extracted.status not in ("success", "success_with_warning"):
            raise RuntimeError(f"{path.name}: {extracted.error or extracted.status}")
        fps = extracted.fps
        if capture is not None:
            if extracted.decoded_frames != capture["frames_written"]:
                raise ValueError(f"Decoded frame count disagrees with capture report: {path.name}")
            fps = capture["observed_fps"]
        signals = compute_kinematic_signals(extracted.arrays, config.to_segmentation_config())
        extended = continue_with_pose(signals, fps, config.k_on)
        baseline = split_sign_sequence(extracted.arrays, cfg=config, infer_fn=infer)
        candidate = split_sign_sequence(extracted.arrays, cfg=config, infer_fn=infer,
                                        active_filter=lambda _: extended)
        baseline_report = sequence_report(baseline)
        added = extended & ~signals["active_raw"]
        guarded = recover_one_short_segment(extracted.arrays, baseline_report, added, config, infer)
        row = {"clip": path.name, "clip_sha256": digest(path), "group": group, "expected": expected,
               "capture_report_id": report_id, "fps": fps, "decoded_frames": extracted.decoded_frames,
               "added_active_frames": np.flatnonzero(added).tolist(), "baseline": baseline_report,
               "pose_continuation": sequence_report(candidate), "recover_one_short": guarded}
        rows.append(row)
        print(json.dumps({"clip": path.name, "baseline": row["baseline"]["labels"],
                          "pose_continuation": row["pose_continuation"]["labels"],
                          "recover_one_short": guarded["labels"], "guarded_accepted": guarded["accepted"]},
                         ensure_ascii=False), flush=True)

    arms = ("baseline", "pose_continuation", "recover_one_short")
    summary = {group: {arm: summarize([row for row in rows if row["group"] == group], arm)
                       for arm in arms}
               for group in dict.fromkeys(row["group"] for row in rows)}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = ROOT / "outputs" / "segmentation_experiments" / f"hand_dropout_{stamp}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("x", encoding="utf-8") as stream:
        json.dump({"max_dropout_seconds": MAX_DROPOUT_SECONDS, "motion_onset_seconds": MOTION_ONSET_SECONDS,
                   "split_config": baseline["config"], "checkpoint_sha256": rec.checkpoint_sha,
                   "reference_checks": rec.references, "summary": summary, "cases": rows},
                  stream, ensure_ascii=False, indent=2)
    print(json.dumps(summary, indent=2), flush=True)
    print(f"Report: {report_path}", flush=True)


if __name__ == "__main__":
    main()
