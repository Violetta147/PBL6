"""
normalization.py
================
Landmark normalization functions for the VSL400 pipeline.

Two coordinate systems are used (§2, §3):

1. HAND-LOCAL coordinates:
   - Captures HAND SHAPE
   - anchor = wrist (landmark 0)
   - scale  = distance(wrist, middle_MCP)  (landmark 0 → 9)
   - Formula: hand_local = (point - wrist) / hand_scale

2. BODY-RELATIVE coordinates:
   - Captures WHERE THE HAND IS RELATIVE TO THE BODY
   - anchor = midpoint(left_shoulder, right_shoulder)
   - scale  = distance(left_shoulder, right_shoulder)
   - Formula: body_relative = (point - body_origin) / body_scale

They are COMPLEMENTARY. Do NOT replace one with the other (§2).

IMPORTANT (§5, §9):
- NaN is preserved for missing landmarks. NEVER silently replace with zero.
- Epsilon protection against divide-by-zero.
- RAW extraction does NOT interpolate. Temporal repair is a SEPARATE stage.
"""

from __future__ import annotations

import numpy as np


def normalize(
    points: np.ndarray,
    anchor: np.ndarray,
    scale: float,
    epsilon: float = 1e-8,
) -> np.ndarray:
    """Translate points to anchor, then divide by scale.

    Parameters
    ----------
    points : (N, 2) array of XY coordinates.
    anchor : (2,) anchor point (origin of the new coordinate system).
    scale  : scalar divisor. If <= epsilon, returns NaN array.
    epsilon : divide-by-zero protection.

    Returns
    -------
    (N, 2) normalized coordinates. All NaN if scale is too small or
    if inputs contain NaN.
    """
    if scale <= epsilon:
        return np.full_like(points, np.nan, dtype=np.float32)
    if np.any(np.isnan(anchor)):
        return np.full_like(points, np.nan, dtype=np.float32)
    return ((points - anchor) / scale).astype(np.float32)


def compute_hand_scale(
    hand_points: np.ndarray,
    wrist_idx: int = 0,
    middle_mcp_idx: int = 9,
) -> float:
    """Compute hand scale = distance(wrist, middle_MCP).

    This is the scale used in the EXISTING implementation.
    Do NOT silently change this definition (§5, §24).

    Returns NaN if either landmark is NaN.
    """
    wrist = hand_points[wrist_idx]
    mcp = hand_points[middle_mcp_idx]
    if np.any(np.isnan(wrist)) or np.any(np.isnan(mcp)):
        return float("nan")
    return float(np.linalg.norm(wrist - mcp))


def normalize_hand_local(
    hand_points: np.ndarray,
    wrist_idx: int = 0,
    middle_mcp_idx: int = 9,
    epsilon: float = 1e-8,
) -> tuple[np.ndarray, float]:
    """Normalize hand landmarks to wrist-centered, hand-scale coordinates.

    Formula:
        hand_local = (point - wrist) / distance(wrist, middle_MCP)

    Parameters
    ----------
    hand_points : (21, 2) raw image coordinates of hand landmarks.
    wrist_idx : index of wrist landmark (default 0).
    middle_mcp_idx : index of middle finger MCP (default 9).
    epsilon : divide-by-zero protection.

    Returns
    -------
    (hand_local, hand_scale) where:
    - hand_local: (21, 2) normalized coordinates
    - hand_scale: float scalar (distance wrist→middle_MCP). NaN if unavailable.
    """
    if hand_points is None or np.all(np.isnan(hand_points)):
        return (
            np.full((21, 2), np.nan, dtype=np.float32),
            float("nan"),
        )

    hand_scale = compute_hand_scale(hand_points, wrist_idx, middle_mcp_idx)
    anchor = hand_points[wrist_idx]
    hand_local = normalize(hand_points, anchor, hand_scale, epsilon)

    return hand_local, hand_scale


def compute_body_reference(
    pose_points: np.ndarray,
    left_shoulder_idx: int = 1,    # index in POSE_ORDER (not MediaPipe index)
    right_shoulder_idx: int = 2,   # index in POSE_ORDER
    epsilon: float = 1e-8,
) -> tuple[np.ndarray, float, bool]:
    """Compute body origin and scale from shoulder landmarks.

    Formula:
        body_origin = midpoint(left_shoulder, right_shoulder)
        body_scale  = distance(left_shoulder, right_shoulder)

    Parameters
    ----------
    pose_points : (7, 2) raw pose landmarks in POSE_ORDER.
    left_shoulder_idx, right_shoulder_idx : indices within pose_points.
    epsilon : divide-by-zero protection.

    Returns
    -------
    (body_origin, body_scale, valid) where:
    - body_origin: (2,) midpoint of shoulders. NaN if unavailable.
    - body_scale: float shoulder width. NaN if unavailable.
    - valid: bool — False if shoulders are missing or too close.
    """
    l_sh = pose_points[left_shoulder_idx]
    r_sh = pose_points[right_shoulder_idx]

    if np.any(np.isnan(l_sh)) or np.any(np.isnan(r_sh)):
        return np.full(2, np.nan, dtype=np.float32), float("nan"), False

    body_origin = ((l_sh + r_sh) / 2.0).astype(np.float32)
    body_scale = float(np.linalg.norm(l_sh - r_sh))

    if body_scale <= epsilon:
        return body_origin, float("nan"), False

    return body_origin, body_scale, True


def normalize_body(
    pose_points: np.ndarray,
    body_origin: np.ndarray,
    body_scale: float,
    epsilon: float = 1e-8,
) -> np.ndarray:
    """Normalize upper-body landmarks to body-centered coordinates.

    Formula:
        body_norm = (point - body_origin) / body_scale
    """
    return normalize(pose_points, body_origin, body_scale, epsilon)


def normalize_palm_in_body(
    hand_points: np.ndarray,
    palm_indices: list[int],
    body_origin: np.ndarray,
    body_scale: float,
    epsilon: float = 1e-8,
) -> np.ndarray:
    """Extract palm points and normalize to body-centered coordinates.

    This preserves WHERE THE HAND IS relative to the body (§2B).

    Parameters
    ----------
    hand_points : (21, 2) raw image coordinates.
    palm_indices : indices of palm landmarks (default [0,5,9,13,17]).
    body_origin : (2,) body origin.
    body_scale : body scale (shoulder width).

    Returns
    -------
    (len(palm_indices), 2) body-relative palm coordinates.
    """
    if hand_points is None or np.all(np.isnan(hand_points)):
        return np.full((len(palm_indices), 2), np.nan, dtype=np.float32)

    palm_raw = hand_points[palm_indices]
    return normalize(palm_raw, body_origin, body_scale, epsilon)


def compute_hand_body_distances(
    hand_wrist: np.ndarray,
    body_scale: float,
    mouth_point: np.ndarray | None = None,
    chin_point: np.ndarray | None = None,
    same_shoulder: np.ndarray | None = None,
    opposite_shoulder: np.ndarray | None = None,
    include_face: bool = True,
    epsilon: float = 1e-8,
) -> np.ndarray:
    """Compute distances from hand wrist to body reference points.

    All distances are normalized by body_scale (shoulder width).

    Parameters
    ----------
    include_face : if True, returns 4D [mouth, chin, same_shoulder, opp_shoulder];
                   if False, returns 2D [same_shoulder, opp_shoulder] (Issue 10 policy
                   to avoid permanent NaNs when FaceMesh is disabled).

    Returns (4,) or (2,) array with NaN for unavailable reference points.
    """
    if include_face:
        distances = np.full(4, np.nan, dtype=np.float32)
        if np.any(np.isnan(hand_wrist)) or body_scale <= epsilon:
            return distances
        refs = [mouth_point, chin_point, same_shoulder, opposite_shoulder]
        for i, ref in enumerate(refs):
            if ref is not None and not np.any(np.isnan(ref)):
                distances[i] = float(np.linalg.norm(hand_wrist - ref)) / body_scale
        return distances
    else:
        distances = np.full(2, np.nan, dtype=np.float32)
        if np.any(np.isnan(hand_wrist)) or body_scale <= epsilon:
            return distances
        refs = [same_shoulder, opposite_shoulder]
        for i, ref in enumerate(refs):
            if ref is not None and not np.any(np.isnan(ref)):
                distances[i] = float(np.linalg.norm(hand_wrist - ref)) / body_scale
        return distances


def compute_relative_hand_scale(
    hand_scale: float,
    body_scale: float,
    epsilon: float = 1e-8,
) -> float:
    """Compute hand scale relative to body.

    = hand_scale / body_scale

    Proxy for apparent hand size / depth (§5).
    """
    if np.isnan(hand_scale) or np.isnan(body_scale) or body_scale <= epsilon:
        return float("nan")
    return hand_scale / body_scale

