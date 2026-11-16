"""Multi-sign sequence segmentation, sliding-window baseline, and hybrid multi-crop TTA.

Implements Modes 2 and 3 from `02_TEMPORAL_SEGMENTATION_AND_TRIMMING_PLAN.md`:
- `split_sign_sequence`: 3-state FSM (`REST -> SIGNING -> COOLDOWN`) for splitting
  continuous multi-sign sequences into isolated sign segments.
- `sliding_window_infer`: Pure Sliding Window baseline (window W, stride S,
  confidence threshold, and 1D temporal NMS).
- `hybrid_multi_crop_infer`: Stage-2 multi-crop Test-Time Augmentation (K=3
  crops around FSM bounds `[t_s, t_e]` averaging softmax probabilities).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from typing import Any, Callable, Mapping

import numpy as np

try:
    from .boundary_detector import (
        SegmentationConfig,
        compute_kinematic_signals,
        slice_feature_arrays,
    )
except ImportError:  # Allow running directly from segmentation/
    from boundary_detector import (
        SegmentationConfig,
        compute_kinematic_signals,
        slice_feature_arrays,
    )

STATE_REST = "REST"
STATE_SIGNING = "SIGNING"
STATE_COOLDOWN = "COOLDOWN"


@dataclass
class SequenceSplitConfig:
    """Hyperparameters for 3-state FSM multi-sign sequence segmentation."""

    y_rest: float = 1.15
    theta_vel: float = 0.035
    median_window: int = 3
    mode: str = "kinematic_wrist_fsm"
    use_pose_wrist_fallback: bool = True
    k_on: int = 4
    k_off: int = 8
    k_resume: int = 1
    min_segment_frames: int = 20
    max_segment_frames: int = 150
    margin_frames: int = 3

    def __post_init__(self) -> None:
        if self.k_on < 1:
            raise ValueError("k_on must be >= 1")
        if self.k_off < 1:
            raise ValueError("k_off must be >= 1")
        if self.k_resume < 1:
            raise ValueError("k_resume must be >= 1")
        if self.min_segment_frames < 1:
            raise ValueError("min_segment_frames must be >= 1")
        if self.max_segment_frames < 1:
            raise ValueError("max_segment_frames must be >= 1")
        if self.min_segment_frames > self.max_segment_frames:
            raise ValueError("min_segment_frames must be <= max_segment_frames")
        if self.margin_frames < 0:
            raise ValueError("margin_frames must be >= 0")
        # Delegate shared kinematic parameter validation
        self.to_segmentation_config()

    def to_segmentation_config(self) -> SegmentationConfig:
        return SegmentationConfig(
            y_rest=self.y_rest,
            theta_vel=self.theta_vel,
            median_window=self.median_window,
            mode=self.mode,
            use_pose_wrist_fallback=self.use_pose_wrist_fallback,
            margin_frames=self.margin_frames,
            max_output_frames=self.max_segment_frames,
        )


def make_slgcn_infer_fn(
    recognizer: Any,
    allow_training_truncation: bool = True,
) -> Callable[[Mapping[str, np.ndarray]], dict[str, Any]]:
    """Wrap a loaded `ClipRecognizer` into an inference callable on sliced feature dicts."""
    idx_to_gloss = recognizer.labels["idx_to_gloss"]
    torch_mod = recognizer.torch
    model = recognizer.model
    prepare_arrays = recognizer.prepare_arrays

    def infer_fn(sub_arrays: Mapping[str, np.ndarray]) -> dict[str, Any]:
        count = len(sub_arrays["upper_body"])
        t0 = time.perf_counter()
        use_trunc = bool(allow_training_truncation and count > 150)
        tensor, quality = prepare_arrays(sub_arrays, allow_training_truncation=use_trunc)
        adapter_ms = (time.perf_counter() - t0) * 1000.0

        t1 = time.perf_counter()
        with torch_mod.inference_mode():
            logits = model(torch_mod.from_numpy(tensor), keep_prob=1.0)
            probs_t = logits.softmax(dim=1)[0]
        forward_ms = (time.perf_counter() - t1) * 1000.0

        probs = probs_t.cpu().numpy().astype(np.float32)
        scores, indexes = probs_t.topk(5)
        top5 = [
            {"index": int(i), "gloss": idx_to_gloss[str(i)], "softmax": float(s)}
            for i, s in zip(indexes.tolist(), scores.tolist())
        ]
        n_src = min(count, 150)
        return {
            "probs": probs,
            "top5": top5,
            "top1_index": top5[0]["index"],
            "top1_gloss": top5[0]["gloss"],
            "top1_softmax": top5[0]["softmax"],
            "adapter_ms": float(adapter_ms),
            "forward_ms": float(forward_ms),
            "missing_before_pct": float(quality["missing_before_pct"]),
            "missing_after_pct": float(quality["missing_after_pct"]),
            "geometry_blocked_frames": int(quality["geometry_blocked"][:n_src].sum()),
            "source_frames": int(count),
        }

    infer_fn.idx_to_gloss = idx_to_gloss  # type: ignore[attr-defined]
    return infer_fn


def _top5_from_probs(
    probs: np.ndarray,
    idx_to_gloss: Mapping[str, str] | None = None,
) -> list[dict[str, Any]]:
    probs_arr = np.asarray(probs, dtype=np.float32)
    k = min(5, len(probs_arr))
    top_idx = np.argsort(-probs_arr)[:k]
    result = []
    for idx in top_idx.tolist():
        gloss = idx_to_gloss.get(str(idx), str(idx)) if idx_to_gloss else str(idx)
        result.append({"index": int(idx), "gloss": gloss, "softmax": float(probs_arr[idx])})
    return result


def split_sign_sequence(
    arrays: Mapping[str, np.ndarray],
    cfg: SequenceSplitConfig | None = None,
    infer_fn: Callable[[Mapping[str, np.ndarray]], dict[str, Any]] | None = None,
    *,
    active_filter: Callable[[np.ndarray], np.ndarray] | None = None,
) -> dict[str, Any]:
    """Split a multi-sign sequence using the 3-state FSM (`REST -> SIGNING -> COOLDOWN`)."""
    cfg = cfg or SequenceSplitConfig()
    t0 = time.perf_counter()

    signals = compute_kinematic_signals(arrays, cfg.to_segmentation_config())
    active = signals["active_raw"]
    if active_filter is not None:
        active = np.asarray(active_filter(active.copy()), dtype=bool)
        if active.shape != signals["active_raw"].shape:
            raise ValueError("The active-frame filter must preserve the shape of active_raw.")
    T = len(active)

    state = STATE_REST
    on_count = 0
    off_count = 0
    resume_count = 0
    seg_start = 0
    last_active = 0
    raw_segments: list[tuple[int, int]] = []
    state_trace: list[str] = []

    for t in range(T):
        is_act = bool(active[t])
        if state == STATE_REST:
            if is_act:
                on_count += 1
                if on_count >= cfg.k_on:
                    seg_start = t - cfg.k_on + 1
                    last_active = t
                    off_count = 0
                    resume_count = 0
                    state = STATE_SIGNING
            else:
                on_count = 0
        elif state == STATE_SIGNING:
            if is_act:
                last_active = t
            else:
                off_count = 1
                resume_count = 0
                if off_count >= cfg.k_off:
                    raw_segments.append((seg_start, last_active + 1))
                    state = STATE_REST
                    on_count = 0
                    off_count = 0
                else:
                    state = STATE_COOLDOWN
        else:  # STATE_COOLDOWN
            if is_act:
                resume_count += 1
                if resume_count >= cfg.k_resume:
                    last_active = t
                    off_count = 0
                    resume_count = 0
                    state = STATE_SIGNING
            else:
                resume_count = 0
                off_count += 1
                if off_count >= cfg.k_off:
                    raw_segments.append((seg_start, last_active + 1))
                    state = STATE_REST
                    on_count = 0
                    off_count = 0
        state_trace.append(state)

    if state in (STATE_SIGNING, STATE_COOLDOWN):
        raw_segments.append((seg_start, last_active + 1))

    # Expand with margin safely without overlapping adjacent segments
    expanded: list[tuple[int, int, int, int]] = []
    length_limited = False
    for idx, (rs, re) in enumerate(raw_segments):
        s = max(0, rs - cfg.margin_frames)
        e = min(T, re + cfg.margin_frames)
        if expanded and s < expanded[-1][1]:
            prev_s, _, prev_rs, prev_re = expanded[-1]
            mid = (prev_re + rs) // 2
            expanded[-1] = (prev_s, max(prev_s + 1, mid), prev_rs, prev_re)
            s = min(re, max(mid, s))
        if (e - s) >= cfg.min_segment_frames:
            seg_len = e - s
            if seg_len <= cfg.max_segment_frames:
                expanded.append((s, e, rs, re))
            else:
                length_limited = True
                n_chunks = (seg_len + cfg.max_segment_frames - 1) // cfg.max_segment_frames
                if (seg_len // n_chunks) >= cfg.min_segment_frames:
                    edges = [s + (i * seg_len) // n_chunks for i in range(n_chunks + 1)]
                    for i in range(n_chunks):
                        cs, ce = edges[i], edges[i + 1]
                        crs = max(cs, rs) if rs < ce else cs
                        cre = min(ce, re) if re > cs else ce
                        if crs >= cre:
                            crs, cre = cs, ce
                        expanded.append((cs, ce, crs, cre))
                else:
                    center = (s + e) // 2
                    half = cfg.max_segment_frames // 2
                    cs = max(s, min(center - half, e - cfg.max_segment_frames))
                    ce = cs + cfg.max_segment_frames
                    expanded.append((cs, ce, max(cs, rs), min(ce, re)))

    segments: list[dict[str, Any]] = []
    for seg_idx, (s, e, rs, re) in enumerate(expanded):
        sub_arrays = slice_feature_arrays(arrays, s, e)
        seg_entry: dict[str, Any] = {
            "segment_id": seg_idx,
            "t_start": int(s),
            "t_end": int(e),
            "raw_t_start": int(rs),
            "raw_t_end": int(re),
            "num_frames": int(e - s),
            "arrays": sub_arrays,
        }
        segments.append(seg_entry)

    fsm_ms = (time.perf_counter() - t0) * 1000.0

    total_adapter_ms = 0.0
    total_forward_ms = 0.0
    if infer_fn is not None:
        for seg_entry in segments:
            try:
                pred = infer_fn(seg_entry["arrays"])
                seg_entry["prediction"] = pred
                seg_entry["error"] = None
                total_adapter_ms += float(pred.get("adapter_ms", 0.0))
                total_forward_ms += float(pred.get("forward_ms", 0.0))
            except Exception as exc:
                seg_entry["prediction"] = None
                seg_entry["error"] = str(exc)

    return {
        "total_frames": int(T),
        "num_raw_segments": len(raw_segments),
        "raw_segment_bounds": raw_segments,
        "length_limited": length_limited,
        "num_segments": len(segments),
        "segments": segments,
        "fsm_ms": float(fsm_ms),
        "total_adapter_ms": float(total_adapter_ms),
        "total_forward_ms": float(total_forward_ms),
        "state_trace": state_trace,
        "signals": signals,
        "config": asdict(cfg),
    }


def _temporal_iou(a_start: int, a_end: int, b_start: int, b_end: int) -> float:
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    if inter == 0:
        return 0.0
    union = max(a_end, b_end) - min(a_start, b_start)
    return float(inter / union) if union > 0 else 0.0


def sliding_window_infer(
    arrays: Mapping[str, np.ndarray],
    infer_fn: Callable[[Mapping[str, np.ndarray]], dict[str, Any]],
    window_size: int = 60,
    stride: int = 15,
    conf_threshold: float = 0.50,
    nms_iou_threshold: float = 0.30,
    min_window_frames: int = 20,
    cover_tail: bool = True,
    class_agnostic_nms: bool = True,
) -> dict[str, Any]:
    """Method 2: Pure Sliding Window inference with confidence threshold & 1D NMS."""
    if window_size < 1 or stride < 1:
        raise ValueError("window_size and stride must be >= 1")
    if min_window_frames < 1:
        raise ValueError("min_window_frames must be >= 1")
    if not (0.0 <= conf_threshold <= 1.0):
        raise ValueError("conf_threshold must be in [0, 1]")
    if not (0.0 <= nms_iou_threshold <= 1.0):
        raise ValueError("nms_iou_threshold must be in [0, 1]")

    T = len(arrays["upper_body"])
    if T == 0:
        raise ValueError("Empty feature sequence.")

    window_bounds: list[tuple[int, int]] = []
    if T <= window_size:
        if T >= min_window_frames:
            window_bounds.append((0, T))
    else:
        s = 0
        while s + window_size <= T:
            window_bounds.append((s, s + window_size))
            s += stride
        if cover_tail and window_bounds and window_bounds[-1][1] < T:
            tail_start = max(0, T - window_size)
            if (tail_start, T) != window_bounds[-1]:
                window_bounds.append((tail_start, T))

    all_windows: list[dict[str, Any]] = []
    total_adapter_ms = 0.0
    total_forward_ms = 0.0
    num_evaluated = 0
    num_skipped = 0

    for w_idx, (s, e) in enumerate(window_bounds):
        sub = slice_feature_arrays(arrays, s, e)
        try:
            pred = infer_fn(sub)
            num_evaluated += 1
            a_ms = float(pred.get("adapter_ms", 0.0))
            f_ms = float(pred.get("forward_ms", 0.0))
            total_adapter_ms += a_ms
            total_forward_ms += f_ms
            score = float(pred["top1_softmax"])
            all_windows.append(
                {
                    "window_id": w_idx,
                    "t_start": int(s),
                    "t_end": int(e),
                    "num_frames": int(e - s),
                    "evaluated": True,
                    "skipped_reason": None,
                    "top1_index": int(pred["top1_index"]),
                    "top1_gloss": str(pred["top1_gloss"]),
                    "top1_softmax": score,
                    "top5": pred.get("top5", []),
                    "missing_after_pct": pred.get("missing_after_pct"),
                    "adapter_ms": a_ms,
                    "forward_ms": f_ms,
                    "above_threshold": bool(score >= conf_threshold),
                }
            )
        except Exception as exc:
            num_skipped += 1
            all_windows.append(
                {
                    "window_id": w_idx,
                    "t_start": int(s),
                    "t_end": int(e),
                    "num_frames": int(e - s),
                    "evaluated": False,
                    "skipped_reason": str(exc),
                    "top1_index": None,
                    "top1_gloss": None,
                    "top1_softmax": 0.0,
                    "top5": [],
                    "missing_after_pct": None,
                    "adapter_ms": 0.0,
                    "forward_ms": 0.0,
                    "above_threshold": False,
                }
            )

    t_nms0 = time.perf_counter()
    candidates = [w for w in all_windows if w["evaluated"] and w["above_threshold"]]
    ordered = sorted(candidates, key=lambda w: (-w["top1_softmax"], w["t_start"]))
    detections: list[dict[str, Any]] = []
    for cand in ordered:
        keep = True
        for kept in detections:
            if not class_agnostic_nms and cand["top1_index"] != kept["top1_index"]:
                continue
            iou = _temporal_iou(
                cand["t_start"], cand["t_end"], kept["t_start"], kept["t_end"]
            )
            if iou > nms_iou_threshold:
                keep = False
                break
        if keep:
            detections.append(cand)
    detections.sort(key=lambda w: w["t_start"])
    nms_ms = (time.perf_counter() - t_nms0) * 1000.0

    return {
        "total_frames": int(T),
        "window_size": int(window_size),
        "stride": int(stride),
        "conf_threshold": float(conf_threshold),
        "nms_iou_threshold": float(nms_iou_threshold),
        "num_windows_total": len(all_windows),
        "num_windows_evaluated": int(num_evaluated),
        "num_windows_skipped": int(num_skipped),
        "num_candidates_above_threshold": len(candidates),
        "num_detections": len(detections),
        "detections": detections,
        "candidates_above_threshold": candidates,
        "all_windows": all_windows,
        "total_adapter_ms": float(total_adapter_ms),
        "total_forward_ms": float(total_forward_ms),
        "nms_ms": float(nms_ms),
    }


def build_multi_crop_bounds(
    t_start: int,
    t_end: int,
    total_frames: int,
    delta: int = 5,
    min_crop_frames: int = 20,
) -> list[tuple[str, int, int]]:
    """Construct K=3 crops (tight, nominal, wide/shifted) around `[t_start, t_end)`."""
    if total_frames <= 0:
        raise ValueError("total_frames must be > 0")
    s = max(0, min(int(t_start), total_frames - 1))
    e = max(s + 1, min(int(t_end), total_frames))
    length = e - s
    delta = max(1, int(delta))

    # 1. Nominal
    nom = (s, e)

    # 2. Tight (+delta, -delta) while respecting min_crop_frames
    if length - 2 * delta >= min_crop_frames:
        tight = (s + delta, e - delta)
    elif length > min_crop_frames:
        shrink = (length - min_crop_frames) // 2
        if shrink > 0:
            tight = (s + shrink, e - shrink)
        else:
            tight = (s + 1, e) if (e - s - 1) >= min_crop_frames else nom
    else:
        tight = nom

    # 3. Wide (-delta, +delta): only emit when at least one boundary actually expands
    wide = (max(0, s - delta), min(total_frames, e + delta))

    crops: list[tuple[str, int, int]] = []
    seen: set[tuple[int, int]] = set()
    for name, bounds in (("tight", tight), ("nominal", nom), ("wide", wide)):
        if bounds not in seen:
            crops.append((name, bounds[0], bounds[1]))
            seen.add(bounds)
    return crops


def hybrid_multi_crop_infer(
    arrays: Mapping[str, np.ndarray],
    bounds_or_segment: tuple[int, int] | Mapping[str, Any],
    infer_fn: Callable[[Mapping[str, np.ndarray]], dict[str, Any]],
    delta: int = 5,
    min_crop_frames: int = 20,
    idx_to_gloss: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Method 3: Evaluate K<=3 crops around `[t_s, t_e]` and average softmax probabilities."""
    T = len(arrays["upper_body"])
    fallback_triggered = False
    if isinstance(bounds_or_segment, Mapping):
        t_s = int(bounds_or_segment["t_start"])
        t_e = int(bounds_or_segment["t_end"])
        fallback_triggered = bool(bounds_or_segment.get("fallback_triggered", False))
    else:
        t_s, t_e = int(bounds_or_segment[0]), int(bounds_or_segment[1])

    if fallback_triggered:
        s_clamped = max(0, min(t_s, max(0, T - 1)))
        e_clamped = max(s_clamped + 1, min(t_e, T))
        crop_specs = [("nominal", s_clamped, e_clamped)]
    else:
        crop_specs = build_multi_crop_bounds(
            t_s, t_e, T, delta=delta, min_crop_frames=min_crop_frames
        )

    if idx_to_gloss is None:
        idx_to_gloss = getattr(infer_fn, "idx_to_gloss", None)

    crop_results: list[dict[str, Any]] = []
    valid_probs: list[np.ndarray] = []
    total_adapter_ms = 0.0
    total_forward_ms = 0.0

    for name, cs, ce in crop_specs:
        sub = slice_feature_arrays(arrays, cs, ce)
        try:
            pred = infer_fn(sub)
            a_ms = float(pred.get("adapter_ms", 0.0))
            f_ms = float(pred.get("forward_ms", 0.0))
            total_adapter_ms += a_ms
            total_forward_ms += f_ms
            if "probs" in pred and pred["probs"] is not None:
                valid_probs.append(np.asarray(pred["probs"], dtype=np.float32))
            crop_results.append(
                {
                    "crop_name": name,
                    "t_start": int(cs),
                    "t_end": int(ce),
                    "num_frames": int(ce - cs),
                    "status": "ok",
                    "error": None,
                    "top1_index": int(pred["top1_index"]),
                    "top1_gloss": str(pred["top1_gloss"]),
                    "top1_softmax": float(pred["top1_softmax"]),
                    "missing_after_pct": pred.get("missing_after_pct"),
                    "adapter_ms": a_ms,
                    "forward_ms": f_ms,
                }
            )
        except Exception as exc:
            crop_results.append(
                {
                    "crop_name": name,
                    "t_start": int(cs),
                    "t_end": int(ce),
                    "num_frames": int(ce - cs),
                    "status": "failed",
                    "error": str(exc),
                    "top1_index": None,
                    "top1_gloss": None,
                    "top1_softmax": 0.0,
                    "missing_after_pct": None,
                    "adapter_ms": 0.0,
                    "forward_ms": 0.0,
                }
            )

    if not valid_probs:
        raise RuntimeError(
            f"All {len(crop_specs)} multi-crop candidates failed for bounds [{t_s}, {t_e})."
        )

    avg_probs = np.mean(np.stack(valid_probs, axis=0), axis=0).astype(np.float32)
    top5 = _top5_from_probs(avg_probs, idx_to_gloss)

    return {
        "t_start": int(t_s),
        "t_end": int(t_e),
        "num_crops_attempted": len(crop_specs),
        "num_crops_succeeded": len(valid_probs),
        "crops": crop_results,
        "probs": avg_probs,
        "top5": top5,
        "top1_index": top5[0]["index"],
        "top1_gloss": top5[0]["gloss"],
        "top1_softmax": top5[0]["softmax"],
        "total_adapter_ms": float(total_adapter_ms),
        "total_forward_ms": float(total_forward_ms),
    }
