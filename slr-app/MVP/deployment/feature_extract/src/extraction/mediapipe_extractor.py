"""
mediapipe_extractor.py
======================
Core MediaPipe landmark extraction for the VSL400 pipeline.

Refactored from the original ``extract_landmarks.py``, preserving good design
(separated feature groups, dual coordinate system, NaN for missing) while
fixing handedness assignment (§6) and adding configurable feature extraction.

Pipeline stage: RAW LANDMARK EXTRACTION (§5)
    RAW VIDEO → RAW LANDMARK EXTRACTION → [QC] → [TEMPORAL REPAIR] → [RESAMPLE]

This module handles ONLY raw extraction. Temporal repair is separate (§5, §10).

Output arrays per video (all with T = decoded_frame_count):
    left_hand_local        (T, 21, 2)  — wrist-centered hand shape
    right_hand_local       (T, 21, 2)
    upper_body             (T, 7, 2)   — body-centered upper-body pose
    left_palm_body         (T, 5, 2)   — palm in body coordinates
    right_palm_body        (T, 5, 2)
    left_hand_body_relations  (T, 4)   — distances to body landmarks
    right_hand_body_relations (T, 4)
    hand_scales            (T, 2)      — relative hand scale (depth proxy)
    detection_masks        (T, 4)      — [pose, face, left_hand, right_hand]
    handedness_valid       (T, 2)      — [left_valid, right_valid] from assignment
    frame_indices          (T,)        — 0-based frame index
    timestamps             (T,)        — frame_idx / fps
    Optional:
        lower_face         (T, 17, 2)  — if face.enabled
        raw_left_hand      (T, 21, 2)  — if raw_coordinates enabled
        raw_right_hand     (T, 21, 2)
        raw_pose           (T, 7, 2)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

try:
    import mediapipe as mp
    mp_hands = mp.solutions.hands
    mp_face_mesh = mp.solutions.face_mesh
    mp_pose = mp.solutions.pose
except ImportError:
    mp = None  # Allow import for testing without mediapipe

from src.extraction.normalization import (
    normalize_hand_local,
    compute_body_reference,
    normalize_body,
    normalize_palm_in_body,
    compute_hand_body_distances,
    compute_relative_hand_scale,
    normalize,
)
from src.extraction.handedness import (
    HandAssignment,
    assign_hands_pose_proximity,
)

logger = logging.getLogger("vsl400.extractor")

# ---------------------------------------------------------------------------
# Landmark index constants (from original extract_landmarks.py)
# ---------------------------------------------------------------------------

# Upper-body pose landmarks — order matters for array construction (§4)
POSE_INDICES = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
}
POSE_ORDER = list(POSE_INDICES.keys())
N_POSE = len(POSE_ORDER)  # 7

# Hand constants
N_HAND_LM = 21
HAND_WRIST = 0
HAND_MIDDLE_MCP = 9
DEFAULT_PALM_INDICES = [0, 5, 9, 13, 17]

# Face constants (lower face only — §7)
LIPS_OUTER_IDX = [61, 40, 37, 0, 267, 270, 291, 321, 17, 91]  # 10 points
JAW_IDX = [172, 150, 176, 152, 400, 379, 397]                  # 7 points
FACE_IDX = LIPS_OUTER_IDX + JAW_IDX                            # 17 points
N_FACE = len(FACE_IDX)
MOUTH_CENTER_IDX = 13  # MediaPipe FaceMesh
CHIN_IDX = 152


def _nan(shape: tuple) -> np.ndarray:
    """Create a NaN-filled float32 array."""
    return np.full(shape, np.nan, dtype=np.float32)


def _xy(landmark) -> np.ndarray:
    """Extract (x, y) from a single MediaPipe landmark.

    Z is NOT used in the baseline (§8). MediaPipe Z is not calibrated
    metric depth. Any XY vs XYZ comparison should be an experiment.
    """
    return np.array([landmark.x, landmark.y], dtype=np.float32)


# ---------------------------------------------------------------------------
# Video-level extraction
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """Complete extraction output for one video."""
    arrays: dict[str, np.ndarray] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
    decoded_frames: int = 0
    fps: float = 0.0
    status: str = "success"  # success | success_with_warning | failed


def extract_video(
    video_path: str | Path,
    cfg: dict[str, Any],
    max_frames: int | None = None,
) -> ExtractionResult:
    """Extract MediaPipe landmarks from a video file.

    Parameters
    ----------
    video_path : path to .mp4 video
    cfg : loaded config dict
    max_frames : limit frame count (for pilot/testing)

    Returns
    -------
    ExtractionResult with arrays, metadata, and diagnostics.
    """
    video_path = Path(video_path)
    result = ExtractionResult()

    # --- Open video (§13) ---
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        result.status = "failed"
        result.error = f"Cannot open video: {video_path}"
        logger.error(result.error)
        return result

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 25.0  # Fallback
        result.warnings.append(f"Could not read FPS, defaulting to {fps}")
    result.fps = fps

    total_frames_reported = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Config values
    mp_cfg = cfg.get("mediapipe", {})
    hand_cfg = cfg.get("hand_normalization", {})
    body_cfg = cfg.get("body_normalization", {})
    hd_cfg = cfg.get("handedness", {})
    face_cfg = cfg.get("face", {})
    epsilon = float(body_cfg.get("epsilon", 1e-8))
    palm_indices = cfg.get("palm_indices", DEFAULT_PALM_INDICES)
    face_enabled = face_cfg.get("enabled", False)
    rel_cfg = cfg.get("relations", {})
    include_face_rel = rel_cfg.get("include_face", face_enabled)
    save_raw = cfg.get("feature_groups", {}).get("raw_coordinates", False)

    # --- Accumulators ---
    all_left_hand_local = []
    all_right_hand_local = []
    all_upper_body = []
    all_left_palm_body = []
    all_right_palm_body = []
    all_left_relations = []
    all_right_relations = []
    all_hand_scales = []
    all_detection_masks = []
    all_handedness_valid = []
    all_frame_indices = []
    all_timestamps = []
    # Optional
    all_lower_face = [] if face_enabled else None
    all_raw_left_hand = [] if save_raw else None
    all_raw_right_hand = [] if save_raw else None
    all_raw_pose = [] if save_raw else None

    # Assignment tracking
    assignment_methods = {"pose_proximity": 0, "tracking": 0, "mediapipe_label": 0, "none": 0}
    uncertain_count = 0
    prev_assignment: HandAssignment | None = None

    # --- MediaPipe initialization ---
    pose_conf = mp_cfg.get("pose", {})
    hand_mp_cfg = mp_cfg.get("hands", {})
    face_mp_cfg = mp_cfg.get("face_mesh", {})

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=pose_conf.get("model_complexity", 1),
        min_detection_confidence=pose_conf.get("min_detection_confidence", 0.5),
        min_tracking_confidence=pose_conf.get("min_tracking_confidence", 0.5),
    ) as pose, \
    mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=hand_mp_cfg.get("max_num_hands", 2),
        min_detection_confidence=hand_mp_cfg.get("min_detection_confidence", 0.5),
        min_tracking_confidence=hand_mp_cfg.get("min_tracking_confidence", 0.5),
    ) as hands, \
    mp_face_mesh.FaceMesh(
        static_image_mode=False,
        max_num_faces=face_mp_cfg.get("max_num_faces", 1),
        min_detection_confidence=face_mp_cfg.get("min_detection_confidence", 0.5),
        min_tracking_confidence=face_mp_cfg.get("min_tracking_confidence", 0.5),
    ) as face_mesh:

        frame_idx = 0
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break
            if max_frames is not None and frame_idx >= max_frames:
                break

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            frame_rgb.flags.writeable = False  # Performance hint

            # --- Run MediaPipe ---
            pose_res = pose.process(frame_rgb)
            hands_res = hands.process(frame_rgb)
            face_res = face_mesh.process(frame_rgb) if face_enabled else None

            # --- Extract frame features ---
            frame_data = _extract_frame(
                frame_idx=frame_idx,
                pose_res=pose_res,
                hands_res=hands_res,
                face_res=face_res,
                cfg=cfg,
                epsilon=epsilon,
                palm_indices=palm_indices,
                face_enabled=face_enabled,
                include_face_rel=include_face_rel,
                save_raw=save_raw,
                prev_assignment=prev_assignment,
            )

            # Accumulate
            all_left_hand_local.append(frame_data["left_hand_local"])
            all_right_hand_local.append(frame_data["right_hand_local"])
            all_upper_body.append(frame_data["upper_body"])
            all_left_palm_body.append(frame_data["left_palm_body"])
            all_right_palm_body.append(frame_data["right_palm_body"])
            all_left_relations.append(frame_data["left_hand_body_relations"])
            all_right_relations.append(frame_data["right_hand_body_relations"])
            all_hand_scales.append(frame_data["hand_scales"])
            all_detection_masks.append(frame_data["detection_mask"])
            all_handedness_valid.append(frame_data["handedness_valid"])
            all_frame_indices.append(frame_idx)
            all_timestamps.append(frame_idx / fps)

            if face_enabled and all_lower_face is not None:
                all_lower_face.append(frame_data.get("lower_face", _nan((N_FACE, 2))))
            if save_raw:
                all_raw_left_hand.append(frame_data.get("raw_left_hand", _nan((N_HAND_LM, 2))))
                all_raw_right_hand.append(frame_data.get("raw_right_hand", _nan((N_HAND_LM, 2))))
                all_raw_pose.append(frame_data.get("raw_pose", _nan((N_POSE, 2))))

            # Track assignment stats
            assignment = frame_data["assignment"]
            assignment_methods[assignment.method] = assignment_methods.get(assignment.method, 0) + 1
            if not assignment.left_valid and not assignment.right_valid and assignment.method != "none":
                uncertain_count += 1

            prev_assignment = assignment
            frame_idx += 1

    cap.release()
    result.decoded_frames = frame_idx

    if frame_idx == 0:
        result.status = "failed"
        result.error = f"No frames decoded from {video_path}"
        logger.error(result.error)
        return result

    # --- Build arrays ---
    result.arrays = {
        "left_hand_local": np.stack(all_left_hand_local),
        "right_hand_local": np.stack(all_right_hand_local),
        "upper_body": np.stack(all_upper_body),
        "left_palm_body": np.stack(all_left_palm_body),
        "right_palm_body": np.stack(all_right_palm_body),
        "left_hand_body_relations": np.stack(all_left_relations),
        "right_hand_body_relations": np.stack(all_right_relations),
        "hand_scales": np.stack(all_hand_scales),
        "detection_masks": np.stack(all_detection_masks),
        "handedness_valid": np.stack(all_handedness_valid),
        "frame_indices": np.array(all_frame_indices, dtype=np.int32),
        "timestamps": np.array(all_timestamps, dtype=np.float32),
    }

    if face_enabled and all_lower_face:
        result.arrays["lower_face"] = np.stack(all_lower_face)
    if save_raw:
        result.arrays["raw_left_hand"] = np.stack(all_raw_left_hand)
        result.arrays["raw_right_hand"] = np.stack(all_raw_right_hand)
        result.arrays["raw_pose"] = np.stack(all_raw_pose)

    # --- Metadata ---
    result.metadata = {
        "preprocessing_version": cfg.get("preprocessing_version", "unknown"),
        "fps": fps,
        "decoded_frames": frame_idx,
        "reported_frames": total_frames_reported,
        "assignment_methods": str(assignment_methods),
        "uncertain_assignments": uncertain_count,
    }

    # --- Warnings ---
    if frame_idx != total_frames_reported and total_frames_reported > 0:
        msg = f"Frame count mismatch: decoded={frame_idx}, reported={total_frames_reported}"
        result.warnings.append(msg)
        logger.warning("%s — %s", video_path.name, msg)

    if uncertain_count > 0:
        msg = f"Uncertain hand assignments: {uncertain_count}/{frame_idx} frames"
        result.warnings.append(msg)
        logger.warning("%s — %s", video_path.name, msg)

    if result.warnings:
        result.status = "success_with_warning"

    logger.info(
        "Extracted %s: %d frames, assignment methods=%s",
        video_path.name, frame_idx, assignment_methods,
    )

    return result


def _extract_frame(
    frame_idx: int,
    pose_res,
    hands_res,
    face_res,
    cfg: dict[str, Any],
    epsilon: float,
    palm_indices: list[int],
    face_enabled: bool,
    include_face_rel: bool,
    save_raw: bool,
    prev_assignment: HandAssignment | None,
) -> dict[str, Any]:
    """Extract and normalize features for a single frame.

    Returns dict with all feature arrays and diagnostics.
    """
    hd_cfg = cfg.get("handedness", {})

    # -------- POSE / BODY --------
    pose_detected = pose_res.pose_landmarks is not None
    raw_pose = _nan((N_POSE, 2))
    body_origin = _nan((2,))
    body_scale = float("nan")
    body_valid = False
    shoulders = {}

    if pose_detected:
        plm = pose_res.pose_landmarks.landmark
        raw_pose = np.stack([_xy(plm[POSE_INDICES[name]]) for name in POSE_ORDER])
        body_origin, body_scale, body_valid = compute_body_reference(
            raw_pose, left_shoulder_idx=1, right_shoulder_idx=2, epsilon=epsilon,
        )
        if body_valid:
            shoulders = {
                "left": raw_pose[1],   # left_shoulder in POSE_ORDER
                "right": raw_pose[2],  # right_shoulder
            }

    upper_body = normalize_body(raw_pose, body_origin, body_scale, epsilon) if body_valid else _nan((N_POSE, 2))

    # -------- HAND ASSIGNMENT (§6) --------
    hand_lm_list = hands_res.multi_hand_landmarks or []
    handedness_list = hands_res.multi_handedness or []

    assignment = assign_hands_pose_proximity(
        hand_landmarks_list=hand_lm_list,
        handedness_list=handedness_list,
        pose_landmarks=pose_res.pose_landmarks,
        proximity_threshold=hd_cfg.get("proximity_threshold", 0.15),
        prev_assignment=prev_assignment,
        use_tracking_fallback=hd_cfg.get("use_tracking_fallback", True),
        use_mediapipe_fallback=hd_cfg.get("use_mediapipe_label_fallback", True),
    )

    # -------- EXTRACT HAND FEATURES --------
    rel_dim = 4 if include_face_rel else 2

    def _get_hand_arrays(hand_idx: int | None, side: str):
        """Extract features for one hand."""
        if hand_idx is None or hand_idx >= len(hand_lm_list):
            return (
                _nan((N_HAND_LM, 2)),  # hand_local
                _nan((len(palm_indices), 2)),  # palm_body
                _nan((rel_dim,)),  # relations
                float("nan"),  # scale
                _nan((N_HAND_LM, 2)),  # raw
            )

        hand_lm = hand_lm_list[hand_idx]
        raw_hand = np.stack([_xy(lm) for lm in hand_lm.landmark])

        # (1) Hand local normalization
        hand_local, hand_scale = normalize_hand_local(
            raw_hand,
            wrist_idx=HAND_WRIST,
            middle_mcp_idx=HAND_MIDDLE_MCP,
            epsilon=epsilon,
        )

        # (2) Palm in body coordinates
        if body_valid:
            palm_body = normalize_palm_in_body(
                raw_hand, palm_indices, body_origin, body_scale, epsilon,
            )
        else:
            palm_body = _nan((len(palm_indices), 2))

        # (3) Hand-to-body distances
        mouth_pt = None
        chin_pt = None
        if include_face_rel and face_enabled and face_res is not None and face_res.multi_face_landmarks:
            flm = face_res.multi_face_landmarks[0].landmark
            mouth_pt = _xy(flm[MOUTH_CENTER_IDX])
            chin_pt = _xy(flm[CHIN_IDX])

        same_sh = shoulders.get(side)
        opp_sh = shoulders.get("right" if side == "left" else "left")

        relations = compute_hand_body_distances(
            hand_wrist=raw_hand[HAND_WRIST],
            body_scale=body_scale if body_valid else 0.0,
            mouth_point=mouth_pt,
            chin_point=chin_pt,
            same_shoulder=same_sh,
            opposite_shoulder=opp_sh,
            include_face=include_face_rel,
            epsilon=epsilon,
        )

        # (4) Relative hand scale
        rel_scale = compute_relative_hand_scale(hand_scale, body_scale, epsilon)

        return hand_local, palm_body, relations, rel_scale, raw_hand

    l_local, l_palm, l_rel, l_scale, l_raw = _get_hand_arrays(assignment.left_hand_idx, "left")
    r_local, r_palm, r_rel, r_scale, r_raw = _get_hand_arrays(assignment.right_hand_idx, "right")

    # -------- FACE (optional, §7) --------
    face_detected = False
    lower_face = _nan((N_FACE, 2))
    if face_enabled and face_res is not None:
        face_detected = bool(face_res.multi_face_landmarks)
        if face_detected and body_valid:
            flm = face_res.multi_face_landmarks[0].landmark
            raw_face = np.stack([_xy(flm[i]) for i in FACE_IDX])
            lower_face = normalize(raw_face, body_origin, body_scale, epsilon)

    # -------- DETECTION MASK --------
    left_hand_detected = assignment.left_hand_idx is not None
    right_hand_detected = assignment.right_hand_idx is not None
    detection_mask = np.array(
        [pose_detected, face_detected, left_hand_detected, right_hand_detected],
        dtype=bool,
    )
    handedness_valid = np.array(
        [assignment.left_valid, assignment.right_valid],
        dtype=bool,
    )

    # -------- ASSEMBLE --------
    frame_data = {
        "left_hand_local": l_local,
        "right_hand_local": r_local,
        "upper_body": upper_body,
        "left_palm_body": l_palm,
        "right_palm_body": r_palm,
        "left_hand_body_relations": l_rel,
        "right_hand_body_relations": r_rel,
        "hand_scales": np.array([l_scale, r_scale], dtype=np.float32),
        "detection_mask": detection_mask,
        "handedness_valid": handedness_valid,
        "assignment": assignment,
    }

    if face_enabled:
        frame_data["lower_face"] = lower_face
    if save_raw:
        frame_data["raw_left_hand"] = l_raw
        frame_data["raw_right_hand"] = r_raw
        frame_data["raw_pose"] = raw_pose

    return frame_data

