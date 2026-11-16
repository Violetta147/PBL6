"""Compare #32 with the frozen kiosk splitter on archived webcam clips."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
import json
import math
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from desktop_mvp.check_clip import ClipRecognizer
from segmentation.sequence_splitter import (
    SequenceSplitConfig,
    make_slgcn_infer_fn,
    split_sign_sequence,
)

REFERENCE_FPS = 15.0
WINDOW_MS = 800
REST_MS = 500
INTERRUPTION_MS = 130
THANKS = "Cảm ơn"
SCARF = "Khăn quàng cổ"


def tolerate_rest_interruptions(active: np.ndarray, fps: float) -> np.ndarray:
    """Bridge only short interior bursts surrounded by measured rest."""
    window = max(1, round(WINDOW_MS * fps / 1000))
    minimum_rest = max(1, round(REST_MS * fps / 1000))
    max_burst = max(1, round(INTERRUPTION_MS * fps / 1000))
    rests = np.concatenate(([0], np.cumsum(~active)))
    transitions = np.flatnonzero(active[1:] != active[:-1]) + 1
    edges = np.concatenate(([0], transitions, [len(active)]))
    filtered = active.copy()
    for start, end in zip(edges[:-1], edges[1:]):
        if start == 0 or end == len(active) or not active[start] or end - start > max_burst:
            continue
        # A full window must contain the burst and at least one rest frame on each side.
        first = max(0, end + 1 - window)
        last = min(start - 1, len(active) - window)
        if any(rests[left + window] - rests[left] >= minimum_rest for left in range(first, last + 1)):
            filtered[start:end] = False
    return filtered


def settings(fps: float) -> dict:
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("The experiment requires a positive observed or estimated FPS.")
    baseline = SequenceSplitConfig()
    timed = replace(
        baseline,
        k_off=max(1, round(baseline.k_off * fps / REFERENCE_FPS)),
        min_segment_frames=min(baseline.max_segment_frames,
                               max(1, round(baseline.min_segment_frames * fps / REFERENCE_FPS))),
    )
    return {
        "baseline": {"cfg": baseline},
        "duration_only": {"cfg": timed},
        "timed_rest": {"cfg": timed, "active_filter": partial(tolerate_rest_interruptions, fps=fps)},
    }


def cases(camera_roll: Path):
    # Labels come from the handoff and the ordered five-file capture table.
    for code, expected in (
        ("23_04_20", [SCARF, THANKS]), ("23_04_34", [THANKS, SCARF]),
        ("23_13_00", [THANKS, SCARF]), ("22_34_23", [SCARF, THANKS]),
        ("22_34_39", [THANKS, SCARF]), ("23_02_55", [THANKS]),
    ):
        yield camera_roll / f"WIN_20261115_{code}_Pro.mp4", "reference", expected, None
    for code, expected in (
        ("01_52_53", [THANKS]), ("01_53_05", [SCARF]),
        ("01_53_21", [THANKS, SCARF]), ("01_53_42", [SCARF, THANKS]),
        ("01_54_02", []),
    ):
        yield camera_roll / f"WIN_20261116_{code}_Pro.mp4", "later_capture", expected, None
    for code in ("021700", "021728", "021806", "022116"):
        path, = (ROOT / "local_data").glob(f"webcam_20261116_{code}_*.avi")
        # The archived kiosk ended these recordings automatically at 13 seconds.
        yield path, "unlabelled_live_failure", None, 13


def kiosk_cases(reports: list[Path]):
    for path in reports:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
        capture = report["capture"]
        if capture["frames_written"] != report["decoded_frames"]:
            raise ValueError(f"{path}: frame counts do not agree.")
        yield Path(report["video"]), "unlabelled_long_live", None, capture["seconds"]


def summarize(rows: list[dict], arm: str) -> dict:
    labelled = [row for row in rows if row["expected"] is not None]
    sequences = [row for row in labelled if len(row["expected"]) > 1]
    singles = [row for row in labelled if len(row["expected"]) == 1]
    negatives = [row for row in labelled if not row["expected"]]
    return {
        "sequences_total": len(sequences),
        "sequences_exact": sum(row[arm]["accepted"] and row[arm]["labels"] == row["expected"]
                               for row in sequences),
        "sequences_too_few_raw_segments": sum(len(row[arm]["raw_bounds"]) < len(row["expected"])
                                             for row in sequences),
        "sequences_too_many_raw_segments": sum(len(row[arm]["raw_bounds"]) > len(row["expected"])
                                              for row in sequences),
        "singles_total": len(singles),
        "singles_exact": sum(row[arm]["labels"] == row["expected"] for row in singles),
        "negative_total": len(negatives),
        "negative_with_labels": sum(bool(row[arm]["labels"]) for row in negatives),
        "negative_accepted_by_kiosk": sum(row[arm]["accepted"] for row in negatives),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--camera-roll", type=Path)
    source.add_argument("--kiosk-report", type=Path, action="append")
    args = parser.parse_args()
    rec = ClipRecognizer()
    infer = make_slgcn_infer_fn(rec, allow_training_truncation=False)
    rows = []
    inputs = cases(args.camera_roll) if args.camera_roll else kiosk_cases(args.kiosk_report)
    for path, group, expected, elapsed in inputs:
        extraction = rec.extract_video(path, rec.config)
        if extraction.error or extraction.status not in ("success", "success_with_warning"):
            raise RuntimeError(f"{path.name}: {extraction.error or extraction.status}")
        fps = extraction.decoded_frames / elapsed if elapsed is not None else extraction.fps
        row = {"clip": path.name, "group": group, "expected": expected, "fps": fps,
               "fps_source": "frame count / capture seconds" if elapsed is not None else "MP4 average",
               "capture_seconds": elapsed,
               "decoded_frames": extraction.decoded_frames}
        arms = settings(fps)
        for name, kwargs in arms.items():
            result = split_sign_sequence(extraction.arrays, infer_fn=infer, **kwargs)
            segments = [{"bounds": [s["t_start"], s["t_end"]],
                         "top5": s["prediction"]["top5"] if s["prediction"] else [],
                         "error": s["error"]} for s in result["segments"]]
            labels = [s["top5"][0]["gloss"] if s["top5"] else None for s in segments]
            raw = result["raw_segment_bounds"]
            row[name] = {
                "labels": labels, "raw_bounds": raw, "segments": segments,
                "length_limited": result["length_limited"], "config": result["config"],
                "accepted": len(raw) >= 2 and len(raw) == len(segments)
                and not result["length_limited"] and all(label is not None for label in labels),
            }
        rows.append(row)
        print(json.dumps({"clip": path.name, **{arm: row[arm]["labels"] for arm in arms}},
                         ensure_ascii=False), flush=True)

    names = settings(REFERENCE_FPS)
    groups = dict.fromkeys(row["group"] for row in rows if row["expected"] is not None)
    summary = {group: {arm: summarize([row for row in rows if row["group"] == group], arm)
                       for arm in names} for group in groups}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = ROOT / "outputs" / "segmentation_experiments" / f"timed_rest_32_{stamp}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as f:
        json.dump({"window_ms": WINDOW_MS, "rest_ms": REST_MS, "interruption_ms": INTERRUPTION_MS,
                   "reference_fps": REFERENCE_FPS, "summary": summary, "cases": rows},
                  f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Report: {destination}")


if __name__ == "__main__":
    main()
