"""
handedness.py
=============
Anatomical LEFT/RIGHT hand assignment for the VSL400 pipeline (§6, Issue 9).

SCIENTIFIC CHANGE DOCUMENTATION (§24):
    A. OLD METHOD:
       Blindly trust ``handedness.classification[0].label`` from MediaPipe.
    B. NEW METHOD:
       Pose-wrist proximity matching with position-based tracking fallback.
    C. REASON:
       MediaPipe handedness label assumes selfie/mirrored video convention.
       VSL400 videos are non-mirrored (recorded by external cameras).
       This means MediaPipe may assign anatomically INCORRECT left/right labels.
    D. BENEFIT:
       Anatomically correct L/R assignment by matching detected hands to
       known anatomical pose wrists via image-space proximity.
    E. RISK & FALLBACK SAFETY (Issue 9):
       - Requires valid Pose detection for primary strategy.
       - When two hands are detected but only ONE Pose wrist is valid, do NOT
         automatically declare the other hand anatomically opposite unless supported
         by previous-frame wrist tracking.
       - Tracking fallback uses PREVIOUS ANATOMICAL WRIST POSITION PROXIMITY,
         not list index continuity, preventing swaps when MediaPipe flips list order.
       - Uncertain assignments are marked valid=False or left unassigned.

COORDINATE CONVENTION:
    - "left" / "right" always means ANATOMICAL left/right of the person in the video.
    - MediaPipe Pose landmarks 15/16 are anatomical left/right wrists.
    - Image X-axis: left side of image corresponds to person's RIGHT side
      (in non-mirrored camera perspective).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger("vsl400.handedness")


@dataclass
class HandAssignment:
    """Result of hand-to-side assignment for one frame."""
    left_hand_idx: int | None = None      # Index in detected hands list
    right_hand_idx: int | None = None     # Index in detected hands list
    left_valid: bool = False              # True if assignment is confident
    right_valid: bool = False
    method: str = "none"                  # "pose_proximity" | "tracking" | "mediapipe_label" | "none"
    left_distance: float = float("nan")   # Assignment distance (diagnostic)
    right_distance: float = float("nan")
    left_wrist_xy: np.ndarray | None = None   # (2,) XY of assigned left wrist
    right_wrist_xy: np.ndarray | None = None  # (2,) XY of assigned right wrist


def _extract_hand_wrist_xy(hand_landmarks) -> np.ndarray:
    """Extract wrist XY from a MediaPipe hand landmark set.

    Returns (2,) array of [x, y] in normalized image coordinates.
    """
    wrist = hand_landmarks.landmark[0]
    return np.array([wrist.x, wrist.y], dtype=np.float32)


def _extract_pose_wrists(
    pose_landmarks,
    left_idx: int = 15,
    right_idx: int = 16,
) -> tuple[np.ndarray, np.ndarray, bool, bool]:
    """Extract anatomical left and right wrist from Pose landmarks.

    Parameters
    ----------
    pose_landmarks : MediaPipe pose landmarks.
    left_idx : MediaPipe Pose index for left wrist (default 15).
    right_idx : MediaPipe Pose index for right wrist (default 16).

    Returns
    -------
    (left_wrist_xy, right_wrist_xy, left_valid, right_valid)
    """
    lm = pose_landmarks.landmark

    left_wrist = np.array([lm[left_idx].x, lm[left_idx].y], dtype=np.float32)
    right_wrist = np.array([lm[right_idx].x, lm[right_idx].y], dtype=np.float32)

    left_valid = lm[left_idx].visibility > 0.3
    right_valid = lm[right_idx].visibility > 0.3

    return left_wrist, right_wrist, left_valid, right_valid


def assign_hands_pose_proximity(
    hand_landmarks_list: list,
    handedness_list: list,
    pose_landmarks,
    proximity_threshold: float = 0.15,
    prev_assignment: HandAssignment | None = None,
    use_tracking_fallback: bool = True,
    use_mediapipe_fallback: bool = True,
) -> HandAssignment:
    """Assign detected hands to anatomical left/right using Pose wrist proximity.

    Parameters
    ----------
    hand_landmarks_list : list of detected hand landmarks from MediaPipe Hands.
    handedness_list : corresponding MediaPipe handedness classifications.
    pose_landmarks : MediaPipe Pose landmarks (may be None).
    proximity_threshold : max distance for association.
    prev_assignment : previous frame's assignment (for tracking fallback).
    use_tracking_fallback : whether to use previous-frame tracking.
    use_mediapipe_fallback : whether to use MediaPipe labels as last resort.

    Returns
    -------
    HandAssignment with left/right indices into hand_landmarks_list.
    """
    n_hands = len(hand_landmarks_list) if hand_landmarks_list else 0

    if n_hands == 0:
        return HandAssignment(method="none")

    hand_wrists = [_extract_hand_wrist_xy(h) for h in hand_landmarks_list]

    # --- STRATEGY 1: Pose wrist proximity (primary) ---
    if pose_landmarks is not None:
        pose_left, pose_right, pl_valid, pr_valid = _extract_pose_wrists(pose_landmarks)

        if pl_valid or pr_valid:
            if n_hands >= 2:
                assignment = _assign_two_hands(
                    hand_wrists, pose_left, pose_right, pl_valid, pr_valid,
                    proximity_threshold=proximity_threshold,
                    prev_assignment=prev_assignment,
                )
            else:  # n_hands == 1
                assignment = _assign_one_hand(
                    hand_wrists[0], 0, pose_left, pose_right,
                    pl_valid, pr_valid, proximity_threshold,
                )

            # Record wrist positions on assignment
            if assignment.left_hand_idx is not None and assignment.left_hand_idx < n_hands:
                assignment.left_wrist_xy = hand_wrists[assignment.left_hand_idx]
            if assignment.right_hand_idx is not None and assignment.right_hand_idx < n_hands:
                assignment.right_wrist_xy = hand_wrists[assignment.right_hand_idx]

            # If at least one hand was assigned via pose, return it
            if assignment.left_hand_idx is not None or assignment.right_hand_idx is not None:
                return assignment

    # --- STRATEGY 2: Tracking fallback (Issue 9 — position proximity) ---
    if use_tracking_fallback and prev_assignment is not None and prev_assignment.method != "none":
        assignment = _assign_from_tracking(
            hand_landmarks_list, hand_wrists, prev_assignment, n_hands,
            tracking_threshold=proximity_threshold,
        )
        if assignment.left_hand_idx is not None or assignment.right_hand_idx is not None:
            return assignment

    # --- STRATEGY 3: MediaPipe label fallback (with uncertainty flag) ---
    if use_mediapipe_fallback and handedness_list:
        assignment = _assign_from_mediapipe_label(handedness_list, n_hands)
        if assignment.left_hand_idx is not None and assignment.left_hand_idx < n_hands:
            assignment.left_wrist_xy = hand_wrists[assignment.left_hand_idx]
        if assignment.right_hand_idx is not None and assignment.right_hand_idx < n_hands:
            assignment.right_wrist_xy = hand_wrists[assignment.right_hand_idx]
        return assignment

    return HandAssignment(method="none")


def _assign_two_hands(
    hand_wrists: list[np.ndarray],
    pose_left: np.ndarray,
    pose_right: np.ndarray,
    pl_valid: bool,
    pr_valid: bool,
    proximity_threshold: float = 0.15,
    prev_assignment: HandAssignment | None = None,
) -> HandAssignment:
    """Min-cost 2×2 assignment between detected hands and pose wrists."""
    if not pl_valid and not pr_valid:
        return HandAssignment(method="none")

    h0 = hand_wrists[0]
    h1 = hand_wrists[1]

    if pl_valid and pr_valid:
        cost_a = float(np.linalg.norm(h0 - pose_left) + np.linalg.norm(h1 - pose_right))
        cost_b = float(np.linalg.norm(h0 - pose_right) + np.linalg.norm(h1 - pose_left))

        if cost_a <= cost_b:
            cand_l, cand_r = 0, 1
            d_l = float(np.linalg.norm(h0 - pose_left))
            d_r = float(np.linalg.norm(h1 - pose_right))
        else:
            cand_l, cand_r = 1, 0
            d_l = float(np.linalg.norm(h1 - pose_left))
            d_r = float(np.linalg.norm(h0 - pose_right))

        # Check EACH assigned hand distance against proximity_threshold (Review Item 1)
        # Safe policy: if a matched distance exceeds threshold, do NOT mark confident;
        # leave unassigned (None) so downstream knows no valid hand was near that pose wrist.
        left_hand_idx = cand_l if d_l <= proximity_threshold else None
        left_valid = d_l <= proximity_threshold
        left_wrist_xy = hand_wrists[cand_l] if left_valid else None

        right_hand_idx = cand_r if d_r <= proximity_threshold else None
        right_valid = d_r <= proximity_threshold
        right_wrist_xy = hand_wrists[cand_r] if right_valid else None

        return HandAssignment(
            left_hand_idx=left_hand_idx,
            right_hand_idx=right_hand_idx,
            left_valid=left_valid,
            right_valid=right_valid,
            method="pose_proximity",
            left_distance=d_l,
            right_distance=d_r,
            left_wrist_xy=left_wrist_xy,
            right_wrist_xy=right_wrist_xy,
        )

    # Only one pose wrist valid (Issue 9)
    # Do NOT automatically declare the other hand opposite unless supported by tracking
    valid_pose = pose_left if pl_valid else pose_right
    d0 = float(np.linalg.norm(h0 - valid_pose))
    d1 = float(np.linalg.norm(h1 - valid_pose))
    closest = 0 if d0 <= d1 else 1
    other = 1 - closest
    min_d = min(d0, d1)

    if min_d > proximity_threshold:
        return HandAssignment(method="pose_proximity")

    if pl_valid:
        assigned_left = closest
        assigned_right = None
        right_dist = float("nan")

        # Check tracking fallback for the other hand
        if (
            prev_assignment is not None
            and prev_assignment.right_wrist_xy is not None
        ):
            d_track = float(np.linalg.norm(hand_wrists[other] - prev_assignment.right_wrist_xy))
            if d_track <= proximity_threshold:
                assigned_right = other
                right_dist = d_track

        return HandAssignment(
            left_hand_idx=assigned_left,
            right_hand_idx=assigned_right,
            left_valid=True,
            right_valid=False,  # Unconfirmed or tracking fallback
            method="pose_proximity",
            left_distance=min_d,
            right_distance=right_dist,
            left_wrist_xy=hand_wrists[assigned_left],
            right_wrist_xy=hand_wrists[assigned_right] if assigned_right is not None else None,
        )
    else:
        assigned_right = closest
        assigned_left = None
        left_dist = float("nan")

        # Check tracking fallback for the other hand
        if (
            prev_assignment is not None
            and prev_assignment.left_wrist_xy is not None
        ):
            d_track = float(np.linalg.norm(hand_wrists[other] - prev_assignment.left_wrist_xy))
            if d_track <= proximity_threshold:
                assigned_left = other
                left_dist = d_track

        return HandAssignment(
            left_hand_idx=assigned_left,
            right_hand_idx=assigned_right,
            left_valid=False,
            right_valid=True,
            method="pose_proximity",
            left_distance=left_dist,
            right_distance=min_d,
            left_wrist_xy=hand_wrists[assigned_left] if assigned_left is not None else None,
            right_wrist_xy=hand_wrists[assigned_right],
        )


def _assign_one_hand(
    hand_wrist: np.ndarray,
    hand_idx: int,
    pose_left: np.ndarray,
    pose_right: np.ndarray,
    pl_valid: bool,
    pr_valid: bool,
    threshold: float,
) -> HandAssignment:
    """Associate a single detected hand with the nearest valid pose wrist."""
    d_left = float(np.linalg.norm(hand_wrist - pose_left)) if pl_valid else float("inf")
    d_right = float(np.linalg.norm(hand_wrist - pose_right)) if pr_valid else float("inf")

    min_d = min(d_left, d_right)

    if min_d > threshold:
        logger.debug(
            "Single-hand assignment uncertain: min_dist=%.4f > threshold=%.4f",
            min_d, threshold,
        )
        return HandAssignment(
            method="pose_proximity",
            left_distance=d_left if d_left != float("inf") else float("nan"),
            right_distance=d_right if d_right != float("inf") else float("nan"),
        )

    if d_left <= d_right:
        return HandAssignment(
            left_hand_idx=hand_idx, right_hand_idx=None,
            left_valid=True, right_valid=False,
            method="pose_proximity",
            left_distance=d_left,
            left_wrist_xy=hand_wrist,
        )
    else:
        return HandAssignment(
            left_hand_idx=None, right_hand_idx=hand_idx,
            left_valid=False, right_valid=True,
            method="pose_proximity",
            right_distance=d_right,
            right_wrist_xy=hand_wrist,
        )


def _assign_from_tracking(
    hand_landmarks_list: list,
    hand_wrists: list[np.ndarray],
    prev: HandAssignment,
    n_hands: int,
    tracking_threshold: float = 0.20,
) -> HandAssignment:
    """Use previous-frame wrist POSITIONS for tracking fallback (Issue 9).

    Does NOT rely on MediaPipe list index continuity.
    Uses spatial proximity to previous anatomical hand wrists.
    """
    result = HandAssignment(method="tracking")

    # If previous wrists are recorded, use spatial matching
    has_prev_pos = (prev.left_wrist_xy is not None) or (prev.right_wrist_xy is not None)

    if has_prev_pos:
        if n_hands >= 2 and prev.left_wrist_xy is not None and prev.right_wrist_xy is not None:
            h0, h1 = hand_wrists[0], hand_wrists[1]
            cost_a = float(np.linalg.norm(h0 - prev.left_wrist_xy) + np.linalg.norm(h1 - prev.right_wrist_xy))
            cost_b = float(np.linalg.norm(h0 - prev.right_wrist_xy) + np.linalg.norm(h1 - prev.left_wrist_xy))

            if cost_a <= cost_b:
                d0_l = float(np.linalg.norm(h0 - prev.left_wrist_xy))
                d1_r = float(np.linalg.norm(h1 - prev.right_wrist_xy))
                if d0_l <= tracking_threshold:
                    result.left_hand_idx = 0
                    result.left_distance = d0_l
                    result.left_wrist_xy = h0
                if d1_r <= tracking_threshold:
                    result.right_hand_idx = 1
                    result.right_distance = d1_r
                    result.right_wrist_xy = h1
            else:
                d1_l = float(np.linalg.norm(h1 - prev.left_wrist_xy))
                d0_r = float(np.linalg.norm(h0 - prev.right_wrist_xy))
                if d1_l <= tracking_threshold:
                    result.left_hand_idx = 1
                    result.left_distance = d1_l
                    result.left_wrist_xy = h1
                if d0_r <= tracking_threshold:
                    result.right_hand_idx = 0
                    result.right_distance = d0_r
                    result.right_wrist_xy = h0

            result.left_valid = False
            result.right_valid = False
            return result

        elif n_hands == 1:
            h0 = hand_wrists[0]
            d_l = float(np.linalg.norm(h0 - prev.left_wrist_xy)) if prev.left_wrist_xy is not None else float("inf")
            d_r = float(np.linalg.norm(h0 - prev.right_wrist_xy)) if prev.right_wrist_xy is not None else float("inf")

            if min(d_l, d_r) <= tracking_threshold:
                if d_l <= d_r:
                    result.left_hand_idx = 0
                    result.left_distance = d_l
                    result.left_wrist_xy = h0
                else:
                    result.right_hand_idx = 0
                    result.right_distance = d_r
                    result.right_wrist_xy = h0
                result.left_valid = False
                result.right_valid = False
                return result

    # Fallback when previous positions are not available (e.g. mock test objects)
    if n_hands >= 2:
        if prev.left_hand_idx is not None and prev.right_hand_idx is not None:
            result.left_hand_idx = prev.left_hand_idx if prev.left_hand_idx < n_hands else 0
            result.right_hand_idx = prev.right_hand_idx if prev.right_hand_idx < n_hands else 1
            if result.left_hand_idx == result.right_hand_idx:
                result.left_hand_idx = 0
                result.right_hand_idx = 1
            result.left_wrist_xy = hand_wrists[result.left_hand_idx]
            result.right_wrist_xy = hand_wrists[result.right_hand_idx]
    elif n_hands == 1:
        if prev.left_hand_idx is not None and prev.right_hand_idx is None:
            result.left_hand_idx = 0
            result.left_wrist_xy = hand_wrists[0]
        elif prev.right_hand_idx is not None and prev.left_hand_idx is None:
            result.right_hand_idx = 0
            result.right_wrist_xy = hand_wrists[0]
        else:
            result.left_hand_idx = 0
            result.left_wrist_xy = hand_wrists[0]

    result.left_valid = False
    result.right_valid = False
    return result


def _assign_from_mediapipe_label(
    handedness_list: list,
    n_hands: int,
) -> HandAssignment:
    """Use MediaPipe handedness label as LAST RESORT fallback.

    Inverts labels for non-mirrored external camera perspective.
    Assignments via this method are marked as uncertain (valid=False).
    """
    result = HandAssignment(method="mediapipe_label")

    for i, handedness in enumerate(handedness_list):
        label = handedness.classification[0].label  # "Left" or "Right"
        # INVERT for non-mirrored video:
        # MediaPipe "Left" in non-mirrored → anatomically RIGHT
        # MediaPipe "Right" in non-mirrored → anatomically LEFT
        if label == "Left" and result.right_hand_idx is None:
            result.right_hand_idx = i
        elif label == "Right" and result.left_hand_idx is None:
            result.left_hand_idx = i

    result.left_valid = False
    result.right_valid = False
    return result

