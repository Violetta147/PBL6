"""Single-sign auto-trimming via Kinematic + Wrist-Height FSM.

Implements Module 02 (`02_TEMPORAL_SEGMENTATION_AND_TRIMMING_PLAN.md`):
- Extracts hand presence H_t, body-normalized wrist Y_t, wrist velocity V_t,
  median-smoothed velocity V_tilde_t, and acceleration A_t directly from
  MediaPipe feature arrays without touching `deployment/`.
- Supports `kinematic_wrist_fsm` (default) and `velocity_only` (ablation).
- Preserves strictly increasing `frame_indices` and `timestamps` so sliced
  feature dicts pass `prepare_clip.validate_features()` 100%.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import time
from typing import Any, Mapping

import numpy as np

VALID_MODES = ("kinematic_wrist_fsm", "velocity_only")
REQUIRED_FEATURE_KEYS = (
    "upper_body",
    "left_hand_local",
    "right_hand_local",
    "left_palm_body",
    "right_palm_body",
    "hand_scales",
    "detection_masks",
    "handedness_valid",
    "frame_indices",
    "timestamps",
)


@dataclass
class SegmentationConfig:
    """Hyperparameters for Kinematic + Wrist-Height boundary detection."""

    y_rest: float = 1.15
    theta_vel: float = 0.035
    median_window: int = 3
    max_internal_gap: int = 5
    margin_frames: int = 3
    min_sign_frames: int = 24
    mode: str = "kinematic_wrist_fsm"
    use_pose_wrist_fallback: bool = True
    use_fallback_invariant: bool = True
    max_output_frames: int = 150

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(
                f"Unsupported segmentation mode {self.mode!r}; expected one of {VALID_MODES}"
            )
        if not np.isfinite(self.y_rest):
            raise ValueError("y_rest must be finite")
        if self.theta_vel < 0 or not np.isfinite(self.theta_vel):
            raise ValueError("theta_vel must be finite and >= 0")
        if self.median_window < 1:
            raise ValueError("median_window must be >= 1")
        if self.max_internal_gap < 0:
            raise ValueError("max_internal_gap must be >= 0")
        if self.margin_frames < 0:
            raise ValueError("margin_frames must be >= 0")
        if self.min_sign_frames < 1:
            raise ValueError("min_sign_frames must be >= 1")
        if self.max_output_frames < 1:
            raise ValueError("max_output_frames must be >= 1")


def _median_filter_1d(signal: np.ndarray, window: int) -> np.ndarray:
    """Edge-padded 1D median filter preserving length T without SciPy."""
    x = np.asarray(signal, dtype=np.float32)
    T = len(x)
    if T == 0 or window <= 1:
        return x.copy()
    if window % 2 == 0:
        window += 1
    pad = window // 2
    padded = np.pad(x, (pad, pad), mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(padded, window)
    return np.median(windows, axis=1).astype(np.float32)


def _fill_short_internal_gaps(mask: np.ndarray, max_gap: int) -> np.ndarray:
    """Fill False runs of length <= max_gap bounded on both sides by True."""
    arr = np.asarray(mask, dtype=bool).copy()
    T = len(arr)
    if T == 0 or max_gap <= 0:
        return arr
    i = 0
    while i < T:
        if not arr[i]:
            start = i
            while i < T and not arr[i]:
                i += 1
            end = i
            if start > 0 and end < T and (end - start) <= max_gap:
                arr[start:end] = True
        else:
            i += 1
    return arr


def _connected_true_components(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return half-open [start, end) intervals of contiguous True runs."""
    arr = np.asarray(mask, dtype=bool)
    T = len(arr)
    if T == 0 or not arr.any():
        return []
    padded = np.r_[False, arr, False].astype(np.int8)
    changes = np.diff(padded)
    starts = np.flatnonzero(changes == 1)
    ends = np.flatnonzero(changes == -1)
    return [(int(s), int(e)) for s, e in zip(starts, ends)]


def compute_kinematic_signals(
    arrays: Mapping[str, np.ndarray],
    cfg: SegmentationConfig | None = None,
) -> dict[str, np.ndarray]:
    """Compute per-frame hand presence, wrist height, velocity, and acceleration.

    Parameters
    ----------
    arrays : dict of extracted feature arrays from `extract_video()`.
    cfg : optional `SegmentationConfig`.

    Returns
    -------
    Dictionary containing `(T, ...)` signals:
    - `hand_present` (H_t)
    - `handedness_any`
    - `left_wrist_xy`, `right_wrist_xy`
    - `wrist_y` (Y_t)
    - `velocity` (V_t)
    - `velocity_smooth` (V_tilde_t)
    - `acceleration` (A_t)
    - `acceleration_smooth`
    - `wrist_in_active_zone`
    - `motion_above_thresh`
    - `active_raw`
    """
    cfg = cfg or SegmentationConfig()
    for key in ("upper_body", "left_palm_body", "right_palm_body", "detection_masks"):
        if key not in arrays:
            raise ValueError(f"Missing required feature key: {key}")

    upper_body = np.asarray(arrays["upper_body"], dtype=np.float32)
    left_palm = np.asarray(arrays["left_palm_body"], dtype=np.float32)
    right_palm = np.asarray(arrays["right_palm_body"], dtype=np.float32)
    det_masks = np.asarray(arrays["detection_masks"])

    T = len(upper_body)
    if T == 0:
        raise ValueError("Cannot compute kinematic signals on empty feature sequence.")
    if upper_body.shape != (T, 7, 2):
        raise ValueError(f"Unexpected upper_body shape: {upper_body.shape}")
    if (
        left_palm.ndim != 3
        or left_palm.shape[0] != T
        or left_palm.shape[1] < 1
        or left_palm.shape[2] != 2
    ):
        raise ValueError(f"Unexpected left_palm_body shape: {left_palm.shape}")
    if (
        right_palm.ndim != 3
        or right_palm.shape[0] != T
        or right_palm.shape[1] < 1
        or right_palm.shape[2] != 2
    ):
        raise ValueError(f"Unexpected right_palm_body shape: {right_palm.shape}")
    if det_masks.shape != (T, 4):
        raise ValueError(f"Unexpected detection_masks shape: {det_masks.shape}")

    hand_present = (det_masks[:, 2].astype(bool)) | (det_masks[:, 3].astype(bool))
    if "handedness_valid" in arrays:
        hv = np.asarray(arrays["handedness_valid"])
        if hv.shape != (T, 2):
            raise ValueError(f"Unexpected handedness_valid shape: {hv.shape}")
        handedness_any = (hv[:, 0].astype(bool)) | (hv[:, 1].astype(bool))
    else:
        handedness_any = hand_present.copy()

    l_palm_w = left_palm[:, 0, :]
    r_palm_w = right_palm[:, 0, :]
    l_pose_w = upper_body[:, 5, :]
    r_pose_w = upper_body[:, 6, :]

    l_palm_ok = np.isfinite(l_palm_w).all(axis=-1)
    r_palm_ok = np.isfinite(r_palm_w).all(axis=-1)
    l_pose_ok = np.isfinite(l_pose_w).all(axis=-1)
    r_pose_ok = np.isfinite(r_pose_w).all(axis=-1)

    if cfg.use_pose_wrist_fallback:
        left_wrist_xy = np.where(l_palm_ok[:, None], l_palm_w, l_pose_w).astype(np.float32)
        right_wrist_xy = np.where(r_palm_ok[:, None], r_palm_w, r_pose_w).astype(np.float32)
    else:
        left_wrist_xy = np.where(l_palm_ok[:, None], l_palm_w, np.nan).astype(np.float32)
        right_wrist_xy = np.where(r_palm_ok[:, None], r_palm_w, np.nan).astype(np.float32)

    # Body-normalized wrist Y_t: minimum y (higher in image) across valid wrists.
    # Prefer detected palm_body wrists whenever available so a noisy undetected
    # pose wrist does not override a genuinely lowered hand.
    wrist_y = np.full(T, np.nan, dtype=np.float32)
    palm_any_ok = l_palm_ok | r_palm_ok
    if palm_any_ok.any():
        ly_p = np.where(l_palm_ok, l_palm_w[:, 1], np.inf)
        ry_p = np.where(r_palm_ok, r_palm_w[:, 1], np.inf)
        min_palm_y = np.minimum(ly_p, ry_p)
        wrist_y[palm_any_ok] = min_palm_y[palm_any_ok]

    if cfg.use_pose_wrist_fallback:
        need_fb = (~palm_any_ok) & (l_pose_ok | r_pose_ok)
        if need_fb.any():
            ly_u = np.where(l_pose_ok, l_pose_w[:, 1], np.inf)
            ry_u = np.where(r_pose_ok, r_pose_w[:, 1], np.inf)
            min_pose_y = np.minimum(ly_u, ry_u)
            wrist_y[need_fb] = min_pose_y[need_fb]

    # Step velocity V_t: prefer same-source displacements to prevent jumps when
    # switching between palm_body and pose fallback on adjacent frames.
    velocity = np.zeros(T, dtype=np.float32)
    if T > 1:
        v_left = np.full(T, -1.0, dtype=np.float32)
        v_right = np.full(T, -1.0, dtype=np.float32)

        for v_arr, palm_w, palm_ok, pose_w, pose_ok in (
            (v_left, l_palm_w, l_palm_ok, l_pose_w, l_pose_ok),
            (v_right, r_palm_w, r_palm_ok, r_pose_w, r_pose_ok),
        ):
            both_palm = palm_ok[1:] & palm_ok[:-1]
            if both_palm.any():
                diff_p = palm_w[1:][both_palm] - palm_w[:-1][both_palm]
                v_arr[1:][both_palm] = np.linalg.norm(diff_p, axis=-1)
            if cfg.use_pose_wrist_fallback:
                both_pose = (~both_palm) & pose_ok[1:] & pose_ok[:-1]
                if both_pose.any():
                    diff_u = pose_w[1:][both_pose] - pose_w[:-1][both_pose]
                    v_arr[1:][both_pose] = np.linalg.norm(diff_u, axis=-1)

        v_max = np.maximum(v_left, v_right)
        velocity = np.where(v_max >= 0.0, v_max, 0.0).astype(np.float32)
        velocity[0] = 0.0

    velocity_smooth = _median_filter_1d(velocity, cfg.median_window)
    acceleration = np.zeros(T, dtype=np.float32)
    acceleration_smooth = np.zeros(T, dtype=np.float32)
    if T > 1:
        acceleration[1:] = np.abs(velocity[1:] - velocity[:-1]).astype(np.float32)
        acceleration_smooth[1:] = np.abs(
            velocity_smooth[1:] - velocity_smooth[:-1]
        ).astype(np.float32)

    wrist_in_active_zone = np.isfinite(wrist_y) & (wrist_y <= cfg.y_rest)
    motion_above_thresh = velocity_smooth >= cfg.theta_vel

    if cfg.mode == "kinematic_wrist_fsm":
        active_raw = (hand_present & wrist_in_active_zone) | (
            hand_present & motion_above_thresh
        )
    elif cfg.mode == "velocity_only":
        active_raw = hand_present & motion_above_thresh
    else:
        raise ValueError(f"Unsupported mode: {cfg.mode}")

    return {
        "hand_present": hand_present.astype(bool),
        "handedness_any": handedness_any.astype(bool),
        "left_wrist_xy": left_wrist_xy,
        "right_wrist_xy": right_wrist_xy,
        "wrist_y": wrist_y,
        "velocity": velocity,
        "velocity_smooth": velocity_smooth,
        "acceleration": acceleration,
        "acceleration_smooth": acceleration_smooth,
        "wrist_in_active_zone": wrist_in_active_zone.astype(bool),
        "motion_above_thresh": motion_above_thresh.astype(bool),
        "active_raw": active_raw.astype(bool),
    }


def detect_single_sign_bounds(
    arrays: Mapping[str, np.ndarray],
    cfg: SegmentationConfig | None = None,
) -> dict[str, Any]:
    """Detect optimal `[t_start, t_end)` active sign bounds for an isolated clip."""
    cfg = cfg or SegmentationConfig()
    t0 = time.perf_counter()
    signals = compute_kinematic_signals(arrays, cfg)
    T = len(signals["active_raw"])
    active_raw = signals["active_raw"]
    active_filled = _fill_short_internal_gaps(active_raw, cfg.max_internal_gap)
    components = _connected_true_components(active_filled)

    fallback_triggered = False
    fallback_reason: str | None = None

    if not components:
        raw_start, raw_end = 0, 0
        if cfg.use_fallback_invariant:
            t_start, t_end = 0, min(T, cfg.max_output_frames)
            fallback_triggered = True
            fallback_reason = "no_active_frames"
        else:
            t_start, t_end = 0, 0
    else:
        # Select longest connected component (tie-break: more raw active frames, then earliest)
        best_comp = max(
            components,
            key=lambda c: (c[1] - c[0], int(active_raw[c[0]:c[1]].sum()), -c[0]),
        )
        raw_start, raw_end = best_comp
        cand_start = max(0, raw_start - cfg.margin_frames)
        cand_end = min(T, raw_end + cfg.margin_frames)
        if cfg.use_fallback_invariant and (cand_end - cand_start) < cfg.min_sign_frames:
            fallback_triggered = True
            fallback_reason = (
                f"below_min_sign_frames({cand_end - cand_start}<{cfg.min_sign_frames})"
            )
            if T <= cfg.max_output_frames:
                t_start, t_end = 0, T
            else:
                center = (raw_start + raw_end) // 2
                half = cfg.max_output_frames // 2
                t_start = max(0, min(center - half, T - cfg.max_output_frames))
                t_end = t_start + cfg.max_output_frames
        else:
            t_start, t_end = cand_start, cand_end

    if (t_end - t_start) > cfg.max_output_frames:
        center = (t_start + t_end) // 2
        half = cfg.max_output_frames // 2
        t_start = max(0, center - half)
        t_end = t_start + cfg.max_output_frames
        if t_end > T:
            t_end = T
            t_start = max(0, T - cfg.max_output_frames)

    fsm_ms = (time.perf_counter() - t0) * 1000.0
    kept_frames = int(max(0, t_end - t_start))

    return {
        "t_start": int(t_start),
        "t_end": int(t_end),
        "raw_t_start": int(raw_start),
        "raw_t_end": int(raw_end),
        "total_frames": int(T),
        "trimmed_frames": kept_frames,
        "kept_ratio": float(kept_frames / T) if T > 0 else 0.0,
        "active_raw_frames": int(active_raw.sum()),
        "active_filled_frames": int(active_filled.sum()),
        "fallback_triggered": bool(fallback_triggered),
        "fallback_reason": fallback_reason,
        "num_components": len(components),
        "components": components,
        "mode": cfg.mode,
        "config": asdict(cfg),
        "fsm_ms": float(fsm_ms),
        "active_mask": active_filled,
        "signals": signals,
    }


def slice_feature_arrays(
    arrays: Mapping[str, np.ndarray],
    start: int,
    end: int,
) -> dict[str, np.ndarray]:
    """Slice extracted feature dict to `[start, end)` preserving `validate_features()` invariants."""
    if "upper_body" not in arrays:
        raise ValueError("Missing 'upper_body' in feature arrays.")
    T = len(arrays["upper_body"])
    start_i = int(start)
    end_i = int(end)
    if start_i < 0 or end_i > T or start_i >= end_i:
        raise ValueError(
            f"Invalid slice bounds [{start_i}, {end_i}) for sequence of length {T}."
        )

    sliced: dict[str, np.ndarray] = {}
    for key, value in arrays.items():
        if isinstance(value, np.ndarray):
            if value.ndim >= 1 and len(value) == T:
                sliced[key] = value[start_i:end_i].copy()
            else:
                sliced[key] = value.copy()
        else:
            sliced[key] = value

    n = end_i - start_i
    # Guarantee finite, integer, strictly increasing frame_indices
    if "frame_indices" in sliced:
        fi = np.asarray(sliced["frame_indices"])
        valid_fi = (
            fi.shape == (n,)
            and np.isfinite(fi).all()
            and np.equal(fi, np.floor(fi)).all()
            and (n <= 1 or (np.diff(fi) > 0).all())
        )
        if not valid_fi:
            sliced["frame_indices"] = np.arange(n, dtype=np.int32)
        else:
            sliced["frame_indices"] = fi.astype(np.int32, copy=False)
    else:
        sliced["frame_indices"] = np.arange(n, dtype=np.int32)

    # Guarantee finite, strictly increasing timestamps
    if "timestamps" in sliced:
        ts = np.asarray(sliced["timestamps"], dtype=np.float64)
        valid_ts = (
            ts.shape == (n,)
            and np.isfinite(ts).all()
            and (n <= 1 or (np.diff(ts) > 0).all())
        )
        if not valid_ts:
            diffs = np.diff(ts[np.isfinite(ts)]) if np.isfinite(ts).sum() > 1 else np.array([])
            pos_diffs = diffs[diffs > 0]
            dt = float(np.median(pos_diffs)) if len(pos_diffs) > 0 else (1.0 / 30.0)
            sliced["timestamps"] = (np.arange(n, dtype=np.float64) * dt).astype(np.float32)
        else:
            # Verify float32 cast remains strictly increasing
            ts32 = ts.astype(np.float32)
            if n > 1 and not (np.diff(ts32) > 0).all():
                diffs = np.diff(ts)
                pos_diffs = diffs[diffs > 0]
                dt = float(np.median(pos_diffs)) if len(pos_diffs) > 0 else (1.0 / 30.0)
                sliced["timestamps"] = (np.arange(n, dtype=np.float64) * dt).astype(np.float32)
            else:
                sliced["timestamps"] = ts32
    else:
        sliced["timestamps"] = (np.arange(n, dtype=np.float32) / np.float32(30.0)).astype(
            np.float32
        )

    return sliced


def trim_single_sign(
    arrays: Mapping[str, np.ndarray],
    cfg: SegmentationConfig | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Detect sign boundaries and return `(trimmed_arrays, bounds_info)`."""
    t0 = time.perf_counter()
    bounds = detect_single_sign_bounds(arrays, cfg)
    if bounds["t_end"] <= bounds["t_start"]:
        raise ValueError(
            "No active sign boundaries detected and use_fallback_invariant=False."
        )
    sliced = slice_feature_arrays(arrays, bounds["t_start"], bounds["t_end"])
    bounds["fsm_with_slice_ms"] = (time.perf_counter() - t0) * 1000.0
    return sliced, bounds
