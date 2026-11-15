"""
repair.py
=========
Temporal gap repair for extracted landmarks (§9, §10).

This is a SEPARATE STAGE from raw extraction (§5).

Pipeline order:
    RAW VIDEO → RAW EXTRACTION → QC → TEMPORAL REPAIR → RESAMPLE → TRAINING TENSOR

Configurable policies:
    SHORT INTERNAL GAP: linear interpolation (up to max_interpolation_gap frames)
    EDGE GAP: nearest valid value or preserve NaN (configurable)
    LONG GAP: do NOT blindly interpolate; retain masks and flag sample

IMPORTANT (§9):
    - Do NOT hard-code arbitrary gap thresholds without exposing in config.
    - All policies must be documented.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger("vsl400.temporal")


def repair_landmarks(
    arrays: dict[str, np.ndarray],
    cfg: dict[str, Any],
) -> tuple[dict[str, np.ndarray], list[str]]:
    """Apply temporal gap repair to extracted landmark arrays.

    Parameters
    ----------
    arrays : dict of (T, ...) landmark arrays from extraction.
    cfg : config dict with temporal.repair settings.

    Returns
    -------
    (repaired_arrays, warnings) where repaired_arrays is a new dict
    with interpolated values, and warnings list gap issues.
    """
    temporal_cfg = cfg.get("temporal", {}).get("repair", {})
    max_gap = temporal_cfg.get("max_interpolation_gap", 5)
    edge_policy = temporal_cfg.get("edge_gap_policy", "nearest")
    long_gap_threshold = temporal_cfg.get("long_gap_warning_threshold", 10)

    warnings = []
    repaired = {}

    # Feature arrays to repair (skip masks, indices, metadata)
    repair_keys = [
        "left_hand_local", "right_hand_local", "upper_body",
        "left_palm_body", "right_palm_body",
        "left_hand_body_relations", "right_hand_body_relations",
        "hand_scales",
    ]
    # Optional
    if "lower_face" in arrays:
        repair_keys.append("lower_face")

    for key in arrays:
        if key in repair_keys:
            arr = arrays[key].copy()
            arr, key_warnings = _repair_array(
                arr, key, max_gap, edge_policy, long_gap_threshold,
            )
            repaired[key] = arr
            warnings.extend(key_warnings)
        else:
            # Pass through unchanged (masks, indices, metadata)
            repaired[key] = arrays[key].copy()

    return repaired, warnings


def _repair_array(
    arr: np.ndarray,
    name: str,
    max_gap: int,
    edge_policy: str,
    long_gap_threshold: int,
) -> tuple[np.ndarray, list[str]]:
    """Repair NaN gaps in a single (T, ...) array.

    Operates on each feature dimension independently.
    """
    warnings = []
    if arr.ndim < 1 or len(arr) == 0:
        return arr, warnings

    original_shape = arr.shape
    T = arr.shape[0]

    # Flatten spatial dimensions: (T, ...) -> (T, D)
    arr_2d = arr.reshape(T, -1).astype(np.float64)
    D = arr_2d.shape[1]

    for d in range(D):
        col = arr_2d[:, d]
        valid_mask = ~np.isnan(col)

        if valid_mask.all():
            continue
        if not valid_mask.any():
            # Entire column is NaN — nothing to repair
            continue

        gaps = _find_gaps(valid_mask)

        for gap_start, gap_end, gap_type in gaps:
            gap_len = gap_end - gap_start

            if gap_type == "internal":
                if gap_len <= max_gap:
                    # Short internal gap: linear interpolation
                    left_val = col[gap_start - 1]
                    right_val = col[gap_end]
                    interp = np.linspace(left_val, right_val, gap_len + 2)[1:-1]
                    col[gap_start:gap_end] = interp
                else:
                    if gap_len >= long_gap_threshold:
                        warnings.append(
                            f"{name}[dim={d}]: long internal gap "
                            f"frames {gap_start}-{gap_end} ({gap_len} frames)"
                        )
                    # Long gap: do NOT interpolate. Retain NaN.

            elif gap_type == "leading":
                if edge_policy == "nearest":
                    first_valid = np.argmax(valid_mask)
                    col[:first_valid] = col[first_valid]
                # else: "nan" — leave as NaN

            elif gap_type == "trailing":
                if edge_policy == "nearest":
                    last_valid = T - 1 - np.argmax(valid_mask[::-1])
                    col[last_valid + 1:] = col[last_valid]
                # else: leave as NaN

        arr_2d[:, d] = col

    repaired = arr_2d.reshape(original_shape).astype(np.float32)
    return repaired, warnings


def _find_gaps(valid_mask: np.ndarray) -> list[tuple[int, int, str]]:
    """Find contiguous NaN gaps in a 1D boolean validity mask.

    Returns list of (start, end, type) where:
    - start: first NaN index
    - end: first valid index after gap (or T for trailing)
    - type: "leading" | "trailing" | "internal"
    """
    T = len(valid_mask)
    gaps = []

    if T == 0:
        return gaps

    i = 0
    while i < T:
        if not valid_mask[i]:
            start = i
            while i < T and not valid_mask[i]:
                i += 1
            end = i

            if start == 0:
                gap_type = "leading"
            elif end == T:
                gap_type = "trailing"
            else:
                gap_type = "internal"

            gaps.append((start, end, gap_type))
        else:
            i += 1

    return gaps
