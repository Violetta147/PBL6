"""Warm-loaded SL-GCN 07b classifier with clean Vision/Inference split for M2.1 & M2.2."""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from deployment.m1.common import DEFAULT_BUNDLE, ROOT

LOW_CONFIDENCE_THRESHOLD = 0.50

BONE_WIRE_KEYS = (
    "xy",
    "usable_mask",
    "observed_mask",
    "imputed_mask",
    "timestamps",
    "frame_indices",
    "association_method",
    "normalization_fallback",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_utf8(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def verify_bundle_utf8(bundle: Path = DEFAULT_BUNDLE) -> dict[str, Any]:
    """UTF-8 safe equivalent of M1 check_bundle (safe on Windows without -X utf8)."""
    bundle = Path(bundle).resolve()
    required = ["best.pt", "best.pt.sha256", "config.json", "label_map.json"]
    missing = [name for name in required if not (bundle / name).is_file()]
    if missing:
        raise ValueError(f"Missing 07b bundle files in {bundle}: {', '.join(missing)}")

    config = _read_json_utf8(bundle / "config.json")
    expected_fields = {
        "model_variant": "slgcn_bone_07b_revamped_100_150",
        "stream": "bone",
        "feature_shape": [150, 28, 8],
    }
    for key, expected in expected_fields.items():
        if config.get(key) != expected:
            raise ValueError(f"07b config mismatch: {key}")

    labels = _read_json_utf8(bundle / "label_map.json")
    if not isinstance(labels, dict) or sorted(labels.values()) != list(range(400)):
        raise ValueError("Expected 400 unique contiguous label IDs")

    digest = _sha256(bundle / "best.pt")
    expected_digest = (bundle / "best.pt.sha256").read_text(encoding="utf-8").split()[0]
    if digest != expected_digest:
        raise ValueError("Checkpoint checksum mismatch")

    hashes = config.get("code_hashes", {})
    if "slgcn_bone_07b.py" not in hashes:
        raise ValueError("Missing frozen 07b code hashes")
    for name, expected_hash in hashes.items():
        code_path = (bundle / "code" / name).resolve()
        if not code_path.is_relative_to(bundle / "code") or not code_path.is_file():
            raise ValueError(f"Frozen source missing: {name}")
        if _sha256(code_path) != expected_hash:
            raise ValueError(f"Frozen source checksum mismatch: {name}")

    return {
        "bundle": str(bundle),
        "checkpoint_sha256": digest,
        "config_sha256": _sha256(bundle / "config.json"),
        "labels": labels,
    }


def serialize_landmark_arrays(arrays: dict[str, np.ndarray]) -> bytes:
    """Pack the 8 bone-adapter keys into a pickle-free compressed NPZ payload."""
    missing = [key for key in BONE_WIRE_KEYS if key not in arrays]
    if missing:
        raise ValueError(f"Missing landmark wire keys: {', '.join(missing)}")
    packed: dict[str, np.ndarray] = {}
    for key in BONE_WIRE_KEYS:
        if key == "association_method":
            # Fixed-width Unicode ensures np.load(..., allow_pickle=False) succeeds.
            packed[key] = np.asarray(arrays[key], dtype=str)
        else:
            packed[key] = np.asarray(arrays[key])
    buf = io.BytesIO()
    np.savez_compressed(buf, **packed)
    return buf.getvalue()


def deserialize_landmark_arrays(payload: bytes) -> dict[str, np.ndarray]:
    """Read compressed NPZ landmark arrays strictly with allow_pickle=False."""
    if not payload:
        raise ValueError("Empty landmark NPZ payload")
    with np.load(io.BytesIO(payload), allow_pickle=False) as npz:
        missing = [key for key in BONE_WIRE_KEYS if key not in npz]
        if missing:
            raise ValueError(f"Missing landmark NPZ keys: {', '.join(missing)}")
        return {key: np.array(npz[key]) for key in BONE_WIRE_KEYS}


def _effective_fps(timestamps: list[float], fallback_fps: float = 30.0) -> float:
    if len(timestamps) >= 2 and timestamps[-1] > timestamps[0]:
        return (len(timestamps) - 1) / (timestamps[-1] - timestamps[0])
    return fallback_fps


def _write_temp_clip(
    frames: list[np.ndarray],
    fps: float,
    prefer_compact: bool = False,
) -> Path:
    """Write buffered BGR frames to a temporary clip (lossless local or compact LAN)."""
    if not frames:
        raise ValueError("Cannot classify empty frame sequence")
    height, width = frames[0].shape[:2]
    safe_fps = float(min(max(fps, 5.0), 60.0))

    fd, raw_path = tempfile.mkstemp(prefix="m2_seg_", suffix=".avi")
    os.close(fd)
    path = Path(raw_path)

    codecs = ("MJPG", "FFV1", "HFYU") if prefer_compact else ("FFV1", "HFYU", "MJPG")
    writer = None
    for codec in codecs:
        candidate = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), safe_fps, (width, height))
        if candidate.isOpened():
            writer = candidate
            break
        candidate.release()

    if writer is None:
        path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to open OpenCV VideoWriter (tried {', '.join(codecs)})")

    try:
        for frame in frames:
            if frame.shape[0] != height or frame.shape[1] != width:
                frame = cv2.resize(frame, (width, height))
            writer.write(frame)
    finally:
        writer.release()

    return path


def encode_frames_to_clip_bytes(
    frames: list[np.ndarray],
    timestamps: list[float],
    fallback_fps: float = 30.0,
    prefer_compact: bool = True,
) -> tuple[bytes, str]:
    """Encode an in-memory segment into clip bytes for LAN vision extraction."""
    fps = _effective_fps(timestamps, fallback_fps=fallback_fps)
    clip_path = _write_temp_clip(frames, fps, prefer_compact=prefer_compact)
    try:
        return clip_path.read_bytes(), ".avi"
    finally:
        clip_path.unlink(missing_ok=True)


class VisionExtractor:
    """Stage A (Vision backend): MediaPipe extraction, crop rescue, and normalization."""

    def __init__(self) -> None:
        for path_str in (str(ROOT / "extraction"), str(ROOT / "preprocessing")):
            if path_str not in sys.path:
                sys.path.insert(0, path_str)

        import extract_raw
        import rescue_candidates
        import pilot_extraction
        import pilot
        import pair_guard

        self._extract_raw = extract_raw
        self._rescue_candidates = rescue_candidates
        self._pilot_extraction = pilot_extraction
        self._pilot = pilot
        self._pair_guard = pair_guard

        self._raw_cfg = _read_json_utf8(ROOT / "extraction/raw_extraction.json")
        self._rescue_policy = _read_json_utf8(ROOT / "extraction/rescue_policy.json")
        self._association = _read_json_utf8(ROOT / "extraction/association_policy.json")
        self._association["ambiguity_margin"] = 0.001

    def extract_landmarks(self, video_path: Path) -> tuple[dict[str, np.ndarray], dict[str, Any], bool, float]:
        """Run M1 raw extraction + optional crop rescue + association + normalization."""
        started = time.perf_counter()
        full, meta = self._extract_raw.extract_video(str(video_path), self._raw_cfg)
        profile = self._rescue_candidates.detector_profile(full, meta["fps"]) | {"view": "front"}
        crop = None
        if self._rescue_candidates.selected(profile, self._rescue_policy):
            roi = self._pilot_extraction.upper_body_crop(full, meta["width"], meta["height"], padding=0.6)
            crop, _ = self._rescue_candidates.extract_crop(str(video_path), full, meta, self._rescue_policy, roi)

        arrays, qc = self._pilot.process(
            full,
            crop,
            meta,
            dict(self._association),
            pair_guard_policy=self._pair_guard.POLICY,
        )
        return arrays, qc, crop is not None, time.perf_counter() - started

    def extract_frames(
        self,
        frames: list[np.ndarray],
        timestamps: list[float],
        fallback_fps: float = 30.0,
    ) -> tuple[dict[str, np.ndarray], dict[str, Any], bool, float]:
        """Run Vision Stage A from an in-memory frame buffer via lossless temp clip."""
        fps = _effective_fps(timestamps, fallback_fps=fallback_fps)
        clip_path = _write_temp_clip(frames, fps, prefer_compact=False)
        try:
            return self.extract_landmarks(clip_path)
        finally:
            clip_path.unlink(missing_ok=True)


class BoneClassifier:
    """Stage B (Pi 4B Edge / CPU): Frozen 07b bone adapter & SL-GCN forward without MediaPipe."""

    def __init__(
        self,
        bundle: Path = DEFAULT_BUNDLE,
        low_confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.bundle = Path(bundle).resolve()
        self.low_confidence_threshold = float(low_confidence_threshold)
        self.identity = verify_bundle_utf8(self.bundle)
        raw_labels = self.identity.pop("labels")
        self.id_to_label: dict[int, str] = {int(v): str(k) for k, v in raw_labels.items()}

        code_dir = str(self.bundle / "code")
        if code_dir not in sys.path:
            sys.path.insert(0, code_dir)

        import torch
        import slgcn_bone_07b as frozen
        import architecture_models

        self._torch = torch
        self._frozen = frozen

        model = architecture_models.build_model("sl_gcn", 400)
        checkpoint = torch.load(self.bundle / "best.pt", map_location="cpu", weights_only=False)
        model.load_state_dict(checkpoint["model"])
        model.float().eval()
        self._model = model
        self._lock = threading.Lock()

    def infer_from_arrays(
        self,
        arrays: dict[str, np.ndarray],
        inference_executor: str = "local",
    ) -> dict[str, Any]:
        """Build 150x28x8 bone window and run warm SL-GCN 07b forward."""
        torch = self._torch
        frozen = self._frozen

        source = object.__new__(frozen.BoneSequenceDataset)
        adapted = source.adapt_clip(arrays)

        class _SingleClip:
            def __len__(self) -> int:
                return 1

            def __getitem__(self, _index: int) -> dict[str, Any]:
                return {key: value.clone() for key, value in adapted.items()}

        window = frozen.BoneWindowDataset(_SingleClip(), training=False)[0]
        inputs = [window[key].unsqueeze(0) for key in ("x", "real", "time")]

        started = time.perf_counter()
        with self._lock, torch.inference_mode():
            logits = self._model(*inputs)[0]
            if not torch.isfinite(logits).all():
                raise ValueError("Non-finite model output")
            scores, indices = logits.softmax(-1).topk(5)
        inference_seconds = time.perf_counter() - started

        top5 = [
            {
                "label": self.id_to_label[int(idx)],
                "label_id": int(idx),
                "score": float(score),
            }
            for idx, score in zip(indices.tolist(), scores.tolist())
        ]
        top1 = top5[0]
        source_frames = int(len(arrays["xy"]))

        return {
            "top1_label": top1["label"],
            "top1_id": top1["label_id"],
            "confidence": top1["score"],
            "low_confidence": top1["score"] < self.low_confidence_threshold,
            "top5": top5,
            "inference_seconds": inference_seconds,
            "inference_executor": inference_executor,
            "source_frames": source_frames,
            "repeated_positions": max(0, 150 - source_frames),
            "truncated_frames": max(0, source_frames - 150),
        }

    def infer_from_npz_bytes(
        self,
        payload: bytes,
        inference_executor: str = "pi_local",
    ) -> dict[str, Any]:
        """Deserialize compressed NPZ landmark arrays and run SL-GCN 07b forward."""
        arrays = deserialize_landmark_arrays(payload)
        return self.infer_from_arrays(arrays, inference_executor=inference_executor)


class SLRClassifier:
    """Unified M2.1 local classifier composing VisionExtractor (Stage A) and BoneClassifier (Stage B)."""

    def __init__(
        self,
        bundle: Path = DEFAULT_BUNDLE,
        low_confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.bundle = Path(bundle).resolve()
        self.low_confidence_threshold = float(low_confidence_threshold)
        self._vision = VisionExtractor()
        self._bone = BoneClassifier(bundle=self.bundle, low_confidence_threshold=self.low_confidence_threshold)
        self.identity = self._bone.identity
        self.id_to_label = self._bone.id_to_label

    def extract_landmarks(self, video_path: Path) -> tuple[dict[str, np.ndarray], dict[str, Any], bool, float]:
        """Stage A (Vision backend): MediaPipe extraction + optional crop rescue + normalization."""
        return self._vision.extract_landmarks(video_path)

    def infer_from_arrays(self, arrays: dict[str, np.ndarray]) -> dict[str, Any]:
        """Stage B (Pi / Classifier): Build 150x28x8 bone window and run warm SL-GCN 07b forward."""
        return self._bone.infer_from_arrays(arrays, inference_executor="local")

    def classify_video(self, video_path: Path) -> dict[str, Any]:
        """Run full M1-parity extraction + inference on a video file."""
        arrays, qc, crop_rescue, preprocess_seconds = self.extract_landmarks(Path(video_path))
        result = self.infer_from_arrays(arrays)
        result.update(
            schema_version="m2.v1",
            model=dict(self.identity),
            preprocessing_seconds=preprocess_seconds,
            crop_rescue=crop_rescue,
            qc=qc,
        )
        return result

    def classify_frames(
        self,
        frames: list[np.ndarray],
        timestamps: list[float],
        fallback_fps: float = 30.0,
    ) -> dict[str, Any]:
        """Classify an in-memory segment slice with exact M1 preprocessing parity."""
        fps = _effective_fps(timestamps, fallback_fps=fallback_fps)
        clip_path = _write_temp_clip(frames, fps, prefer_compact=False)
        try:
            return self.classify_video(clip_path)
        finally:
            clip_path.unlink(missing_ok=True)
