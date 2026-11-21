"""Warm-loaded SL-GCN 07b classifier with clean Vision/Inference split for M2.1 & M2.2."""
from __future__ import annotations

from collections import deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import io
import json
import math
import os
import struct
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
FRAME_BUNDLE_MAGIC = b"PBL6FRM1"
POSE_SLOTS = (11, 12, 13, 14, 15, 16, 23, 24)

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


def encode_frames_to_bundle_bytes(
    frames: list[np.ndarray],
    timestamps: list[float],
    jpeg_quality: int = 85,
) -> bytes:
    """Serialize BGR frames and timestamps as an in-memory JPEG bundle with zero disk I/O."""
    if not frames:
        raise ValueError("Cannot serialize empty frame bundle")
    if len(frames) != len(timestamps):
        raise ValueError("frames and timestamps length mismatch")
    parts = [FRAME_BUNDLE_MAGIC, struct.pack("<I", len(frames))]
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
    for frame, ts in zip(frames, timestamps):
        ok, buf = cv2.imencode(".jpg", frame, encode_params)
        if not ok:
            raise RuntimeError("Failed to JPEG-encode frame for RAM bundle")
        raw = buf.tobytes()
        parts.append(struct.pack("<dI", float(ts), len(raw)))
        parts.append(raw)
    return b"".join(parts)


def decode_bundle_bytes_to_frames(payload: bytes) -> tuple[list[np.ndarray], list[float]]:
    """Decode a PBL6FRM1 byte payload back into BGR frames and float64 timestamps."""
    header_len = len(FRAME_BUNDLE_MAGIC) + 4
    if len(payload) < header_len or not payload.startswith(FRAME_BUNDLE_MAGIC):
        raise ValueError("Invalid PBL6 frame bundle header")
    (count,) = struct.unpack_from("<I", payload, len(FRAME_BUNDLE_MAGIC))
    if count <= 0 or count > 10_000:
        raise ValueError(f"Unsupported frame bundle count: {count}")
    offset = header_len
    frames: list[np.ndarray] = []
    timestamps: list[float] = []
    for _ in range(count):
        if offset + 12 > len(payload):
            raise ValueError("Truncated frame bundle entry header")
        ts, jpg_len = struct.unpack_from("<dI", payload, offset)
        offset += 12
        if jpg_len <= 0 or offset + jpg_len > len(payload):
            raise ValueError("Truncated frame bundle JPEG payload")
        jpg_view = np.frombuffer(payload, dtype=np.uint8, count=jpg_len, offset=offset)
        offset += jpg_len
        bgr = cv2.imdecode(jpg_view, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("Corrupt JPEG image in frame bundle")
        frames.append(bgr)
        timestamps.append(float(ts))
    if offset != len(payload):
        raise ValueError("Trailing bytes in frame bundle payload")
    return frames, timestamps


def extract_pose_8(pose_result: Any) -> tuple[list[list[float]], list[float]]:
    """Extract the 8 M1 torso/arm joints (x, y, z) and visibility scores from MediaPipe Pose."""
    pose = [[0.0, 0.0, 0.0] for _ in range(8)]
    visibility = [0.0] * 8
    if pose_result and pose_result.pose_landmarks:
        landmarks = pose_result.pose_landmarks.landmark
        for slot, joint in enumerate(POSE_SLOTS):
            pt = landmarks[joint]
            x, y, z, vis = float(pt.x), float(pt.y), float(pt.z), float(pt.visibility)
            if math.isfinite(x) and math.isfinite(y) and math.isfinite(z) and math.isfinite(vis):
                pose[slot] = [x, y, z]
                visibility[slot] = vis
    return pose, visibility


def _normalize_timestamps(timestamps: list[float], fallback_fps: float) -> tuple[np.ndarray, float]:
    safe_fps = float(min(max(fallback_fps, 5.0), 60.0))
    default_dt = 1.0 / safe_fps
    norm_ts: list[float] = []
    for idx, raw_t in enumerate(timestamps):
        val = float(raw_t)
        if idx == 0:
            norm_ts.append(max(0.0, val) if math.isfinite(val) else 0.0)
        else:
            prev = norm_ts[-1]
            cand = val if math.isfinite(val) else (prev + default_dt)
            if cand <= prev:
                cand = prev + max(1e-4, default_dt)
            norm_ts.append(cand)
    ts_arr = np.asarray(norm_ts, dtype=np.float64)
    eff_fps = (
        float((len(ts_arr) - 1) / (ts_arr[-1] - ts_arr[0]))
        if len(ts_arr) >= 2 and ts_arr[-1] > ts_arr[0]
        else safe_fps
    )
    return ts_arr, eff_fps


@dataclass
class StreamFrameEntry:
    """Single streamed frame plus MediaPipe extraction state held in Laptop RAM."""

    seq: int
    ts: float
    bgr: np.ndarray
    pose_res: Any
    hand_res: Any | None = None
    packed: dict[str, Any] | None = None


class SessionStreamBuffer:
    """Thread-safe bounded RAM buffer of streamed frames and per-frame MediaPipe detections."""

    def __init__(self, max_seconds: float = 20.0, max_sessions: int = 2) -> None:
        self.max_seconds = float(max_seconds)
        self.max_sessions = max(1, int(max_sessions))
        self._cond = threading.Condition()
        self._sessions: dict[str, list[StreamFrameEntry]] = {}
        self._max_seq: dict[str, int] = {}
        self._session_order: deque[str] = deque()

    def reset(self, session_id: str) -> None:
        with self._cond:
            self._sessions[session_id] = []
            self._max_seq[session_id] = 0
            try:
                self._session_order.remove(session_id)
            except ValueError:
                pass
            self._session_order.append(session_id)
            while len(self._session_order) > self.max_sessions:
                old = self._session_order.popleft()
                if old != session_id:
                    self._sessions.pop(old, None)
                    self._max_seq.pop(old, None)
            self._cond.notify_all()

    def append(self, session_id: str, entry: StreamFrameEntry) -> None:
        with self._cond:
            if session_id not in self._sessions:
                self._sessions[session_id] = []
                self._max_seq[session_id] = 0
                self._session_order.append(session_id)
                while len(self._session_order) > self.max_sessions:
                    old = self._session_order.popleft()
                    if old != session_id:
                        self._sessions.pop(old, None)
                        self._max_seq.pop(old, None)
            buf = self._sessions[session_id]
            if not buf or (entry.ts, entry.seq) >= (buf[-1].ts, buf[-1].seq):
                buf.append(entry)
            else:
                idx = len(buf)
                while idx > 0 and (buf[idx - 1].ts, buf[idx - 1].seq) > (entry.ts, entry.seq):
                    idx -= 1
                buf.insert(idx, entry)
            self._max_seq[session_id] = max(self._max_seq.get(session_id, 0), int(entry.seq))
            cutoff = buf[-1].ts - self.max_seconds
            while len(buf) > 1 and buf[0].ts < cutoff:
                buf.pop(0)
            self._cond.notify_all()

    def wait_and_slice(
        self,
        session_id: str,
        start: float,
        end: float,
        target_seq: int | None = None,
        wait_timeout: float = 0.25,
    ) -> list[StreamFrameEntry]:
        deadline = time.monotonic() + max(0.0, float(wait_timeout))
        with self._cond:
            if session_id not in self._sessions:
                return []
            if target_seq is not None and target_seq > 0:
                while self._max_seq.get(session_id, 0) < target_seq:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    self._cond.wait(timeout=remaining)
            buf = self._sessions.get(session_id, [])
            return [entry for entry in buf if start <= entry.ts <= end]


class VisionExtractor:
    """Stage A (Vision backend): MediaPipe extraction, crop rescue, and normalization."""

    def __init__(self, *, crop_rescue_enabled: bool = False) -> None:
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
        self.crop_rescue_enabled = crop_rescue_enabled

        self._raw_cfg = _read_json_utf8(ROOT / "extraction/raw_extraction.json")
        self._rescue_policy = _read_json_utf8(ROOT / "extraction/rescue_policy.json")
        self._association = _read_json_utf8(ROOT / "extraction/association_policy.json")
        self._association["ambiguity_margin"] = 0.001

        self._mp_lock = threading.Lock()
        self._pose_model: Any = None
        self._hands_model: Any = None
        self._crop_hands_model: Any = None
        self._pool: ThreadPoolExecutor | None = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="m2-vis",
        )

    def _ensure_models_unlocked(self) -> tuple[Any, Any]:
        if self._pose_model is None or self._hands_model is None:
            import mediapipe as mp

            if not hasattr(mp, "solutions"):
                raise RuntimeError("Use the pinned MediaPipe Solutions runtime; see ../README/EXTRACTION.md")
            cfg = self._raw_cfg
            self._pose_model = mp.solutions.pose.Pose(
                static_image_mode=cfg["static_image_mode"],
                enable_segmentation=False,
                **cfg["pose"],
            )
            self._hands_model = mp.solutions.hands.Hands(
                static_image_mode=cfg["static_image_mode"],
                **cfg["hands"],
            )
        return self._pose_model, self._hands_model

    def _ensure_crop_hands_unlocked(self) -> Any:
        if self._crop_hands_model is None:
            import mediapipe as mp

            self._crop_hands_model = mp.solutions.hands.Hands(
                static_image_mode=self._rescue_policy["static_image_mode"],
                **self._rescue_policy["hands"],
            )
        return self._crop_hands_model

    def close(self) -> None:
        with self._mp_lock:
            for attr in ("_pose_model", "_hands_model", "_crop_hands_model"):
                model = getattr(self, attr, None)
                if model is not None:
                    close_fn = getattr(model, "close", None)
                    if callable(close_fn):
                        try:
                            close_fn()
                        except Exception:
                            pass
                    setattr(self, attr, None)
            if self._pool is not None:
                self._pool.shutdown(wait=False)
                self._pool = None

    def reset_stream_models(self) -> None:
        """Reset stateful video-mode MediaPipe trackers between live sessions."""
        with self._mp_lock:
            for attr in ("_pose_model", "_hands_model"):
                model = getattr(self, attr, None)
                if model is not None:
                    close_fn = getattr(model, "close", None)
                    if callable(close_fn):
                        try:
                            close_fn()
                        except Exception:
                            pass
                    setattr(self, attr, None)

    def _should_rescue(self, full: dict[str, np.ndarray], fps: float) -> bool:
        if not self.crop_rescue_enabled:
            return False
        profile = self._rescue_candidates.detector_profile(full, fps) | {"view": "front"}
        return self._rescue_candidates.selected(profile, self._rescue_policy)

    def _run_crop_rescue_unlocked(
        self,
        rgbs: list[np.ndarray],
        full: dict[str, np.ndarray],
        ts_arr: np.ndarray,
        width: int,
        height: int,
    ) -> Any | None:
        roi = self._pilot_extraction.upper_body_crop(full, width, height, padding=0.6)
        x0, y0, x1, y1 = [int(v) for v in roi]
        crop_hands = self._ensure_crop_hands_unlocked()
        crop_packed = []
        for rgb in rgbs:
            crop_rgb = np.ascontiguousarray(rgb[y0:y1, x0:x1])
            crop_rgb.flags.writeable = False
            crop_packed.append(
                self._rescue_candidates.pack_candidates(
                    crop_hands.process(crop_rgb),
                    roi,
                    width,
                    height,
                )
            )
        return self._rescue_candidates.assemble(crop_packed, full, ts_arr * 1000.0, roi)

    def process_stream_frame(
        self,
        bgr: np.ndarray,
        run_hands: bool = False,
    ) -> tuple[list[list[float]], list[float], Any, Any | None, dict[str, Any] | None, float]:
        """Process one streamed camera frame, optionally running Pose || Hands in parallel."""
        started = time.perf_counter()
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        with self._mp_lock:
            pose_model, hands_model = self._ensure_models_unlocked()
            if run_hands:
                if self._pool is None:
                    self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="m2-vis")
                f_pose = self._pool.submit(pose_model.process, rgb)
                f_hands = self._pool.submit(hands_model.process, rgb)
                pose_res = f_pose.result()
                hand_res = f_hands.result()
                packed = self._extract_raw.pack_frame(pose_res, hand_res)
            else:
                pose_res = pose_model.process(rgb)
                hand_res = None
                packed = None
        pose_8, vis_8 = extract_pose_8(pose_res)
        return pose_8, vis_8, pose_res, hand_res, packed, time.perf_counter() - started

    def extract_from_stream_entries(
        self,
        entries: list[StreamFrameEntry],
        fallback_fps: float = 15.0,
    ) -> tuple[dict[str, np.ndarray], dict[str, Any], bool, float, int]:
        """Finalize a sliced segment from Laptop RAM, running catch-up Hands only on missing frames."""
        if not entries:
            raise ValueError("Cannot extract landmarks from empty stream slice")
        started = time.perf_counter()
        ordered = sorted(entries, key=lambda e: (e.ts, e.seq))
        height, width = ordered[0].bgr.shape[:2]
        ts_arr, eff_fps = _normalize_timestamps([e.ts for e in ordered], fallback_fps=fallback_fps)

        crop = None
        rgbs_for_rescue: list[np.ndarray] | None = None
        catchup_hands_frames = 0

        with self._mp_lock:
            _, hands_model = self._ensure_models_unlocked()
            packed_list: list[dict[str, Any]] = []
            for entry in ordered:
                if entry.packed is None:
                    rgb = cv2.cvtColor(entry.bgr, cv2.COLOR_BGR2RGB)
                    rgb.flags.writeable = False
                    hand_res = hands_model.process(rgb)
                    entry.hand_res = hand_res
                    entry.packed = self._extract_raw.pack_frame(entry.pose_res, hand_res)
                    catchup_hands_frames += 1
                packed_list.append(entry.packed)

            full = self._extract_raw.assemble_frames(packed_list, None, height / width)
            full["frame_indices"] = np.arange(len(ordered), dtype=np.int32)
            full["decoder_timestamps"] = ts_arr.copy()
            full["timestamps"] = ts_arr
            self._extract_raw.validate_arrays(full)

            meta: dict[str, Any] = {
                "fps": eff_fps,
                "width": width,
                "height": height,
                "decoded_frames": len(ordered),
            }
            if self._should_rescue(full, eff_fps):
                rgbs_for_rescue = []
                for entry in ordered:
                    frame = entry.bgr
                    if frame.shape[0] != height or frame.shape[1] != width:
                        frame = cv2.resize(frame, (width, height))
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    rgb.flags.writeable = False
                    rgbs_for_rescue.append(rgb)
                crop = self._run_crop_rescue_unlocked(rgbs_for_rescue, full, ts_arr, width, height)

        arrays, qc = self._pilot.process(
            full,
            crop,
            meta,
            dict(self._association),
            pair_guard_policy=self._pair_guard.POLICY,
        )
        return arrays, qc, crop is not None, time.perf_counter() - started, catchup_hands_frames

    def extract_from_frames(
        self,
        frames: list[np.ndarray],
        timestamps: list[float],
        fallback_fps: float = 20.0,
    ) -> tuple[dict[str, np.ndarray], dict[str, Any], bool, float]:
        """Run warm parallel Pose||Hands extraction + crop rescue + M1 normalization in RAM."""
        if not frames:
            raise ValueError("Cannot extract landmarks from empty frame sequence")
        if len(frames) != len(timestamps):
            raise ValueError("frames and timestamps length mismatch")

        started = time.perf_counter()
        height, width = frames[0].shape[:2]
        rgbs: list[np.ndarray] = []
        for frame in frames:
            if frame.shape[0] != height or frame.shape[1] != width:
                frame = cv2.resize(frame, (width, height))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            rgbs.append(rgb)

        ts_arr, eff_fps = _normalize_timestamps(timestamps, fallback_fps=fallback_fps)

        with self._mp_lock:
            pose_model, hands_model = self._ensure_models_unlocked()
            if self._pool is None:
                self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="m2-vis")
            f_pose = self._pool.submit(lambda: [pose_model.process(r) for r in rgbs])
            f_hands = self._pool.submit(lambda: [hands_model.process(r) for r in rgbs])
            pose_outs = f_pose.result()
            hand_outs = f_hands.result()

            packed = [self._extract_raw.pack_frame(p, h) for p, h in zip(pose_outs, hand_outs)]
            full = self._extract_raw.assemble_frames(packed, None, height / width)
            full["frame_indices"] = np.arange(len(frames), dtype=np.int32)
            full["decoder_timestamps"] = ts_arr.copy()
            full["timestamps"] = ts_arr
            self._extract_raw.validate_arrays(full)

            meta: dict[str, Any] = {
                "fps": eff_fps,
                "width": width,
                "height": height,
                "decoded_frames": len(frames),
            }
            crop = None
            if self._should_rescue(full, eff_fps):
                crop = self._run_crop_rescue_unlocked(rgbs, full, ts_arr, width, height)

        arrays, qc = self._pilot.process(
            full,
            crop,
            meta,
            dict(self._association),
            pair_guard_policy=self._pair_guard.POLICY,
        )
        return arrays, qc, crop is not None, time.perf_counter() - started

    def extract_landmarks(self, video_path: Path) -> tuple[dict[str, np.ndarray], dict[str, Any], bool, float]:
        """Run M1 raw extraction + optional crop rescue + association + normalization."""
        started = time.perf_counter()
        full, meta = self._extract_raw.extract_video(str(video_path), self._raw_cfg)
        crop = None
        if self._should_rescue(full, meta["fps"]):
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
        """Run Vision Stage A from an in-memory frame buffer with warm parallel MediaPipe."""
        return self.extract_from_frames(frames, timestamps, fallback_fps=fallback_fps)


class BoneClassifier:
    """Stage B (Pi 4B Edge / CPU): Frozen 07b bone adapter & SL-GCN forward without MediaPipe."""

    def __init__(
        self,
        bundle: Path = DEFAULT_BUNDLE,
        low_confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
        backend: str = "auto",
        onnx_threads: int | None = None,
    ) -> None:
        if backend not in ("auto", "onnx", "torch"):
            raise ValueError(f"Unsupported BoneClassifier backend: {backend}")
        self.bundle = Path(bundle).resolve()
        self.low_confidence_threshold = float(low_confidence_threshold)
        self.identity = verify_bundle_utf8(self.bundle)
        raw_labels = self.identity.pop("labels")
        self.id_to_label: dict[int, str] = {int(v): str(k) for k, v in raw_labels.items()}

        code_dir = str(self.bundle / "code")
        if code_dir not in sys.path:
            sys.path.insert(0, code_dir)

        import architecture_data as arch_data
        import slgcn_bone_07b as frozen

        self._arch_data = arch_data
        self._frozen = frozen
        self._torch: Any = None
        self._model: Any = None
        self._ort_session: Any = None
        self._lock = threading.Lock()

        onnx_path = self.bundle / "slgcn_07b.onnx"
        ort = None
        if backend in ("auto", "onnx"):
            try:
                import onnxruntime as ort_mod

                ort = ort_mod
            except ImportError:
                ort = None

        if backend in ("auto", "onnx") and ort is not None and onnx_path.is_file():
            sess_opts = ort.SessionOptions()
            sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            sess_opts.intra_op_num_threads = int(onnx_threads) if (onnx_threads and onnx_threads > 0) else min(4, os.cpu_count() or 4)
            sess_opts.inter_op_num_threads = 1
            self._ort_session = ort.InferenceSession(
                str(onnx_path),
                sess_options=sess_opts,
                providers=["CPUExecutionProvider"],
            )
            self.runtime_backend = "onnx"
        elif backend == "onnx":
            raise RuntimeError(
                f"ONNX backend requested but model/runtime missing ({onnx_path})"
            )
        else:
            import torch
            import architecture_models

            self._torch = torch
            model = architecture_models.build_model("sl_gcn", 400)
            checkpoint = torch.load(self.bundle / "best.pt", map_location="cpu", weights_only=False)
            model.load_state_dict(checkpoint["model"])
            model.float().eval()
            self._model = model
            self.runtime_backend = "torch"

        self.identity["runtime_backend"] = self.runtime_backend

    def _prepare_bone_input(self, arrays: dict[str, np.ndarray]) -> np.ndarray:
        frozen = self._frozen
        arch_data = self._arch_data
        repaired = frozen.repair(arrays)
        joints = arch_data.joint_features(repaired)[:, arch_data.SL_NODES]
        if not len(joints):
            raise ValueError("Empty landmark sequence")
        frames = int(frozen.CACHE_FRAMES)
        indices = np.arange(frames) % len(joints)
        x = arch_data.bone_features(joints)[indices].astype(np.float32, copy=True)
        valid = x[:, 0, 4] != 0
        if np.any(valid):
            x[valid, 0, :2] -= x[valid, 0, :2].mean(axis=0, keepdims=True)
        return np.ascontiguousarray(x[None, ...], dtype=np.float32)

    def infer_from_arrays(
        self,
        arrays: dict[str, np.ndarray],
        inference_executor: str = "local",
    ) -> dict[str, Any]:
        """Build 150x28x8 bone window and run warm SL-GCN 07b forward."""
        if self.runtime_backend == "onnx":
            x_np = self._prepare_bone_input(arrays)
            started = time.perf_counter()
            with self._lock:
                logits_np = self._ort_session.run(["logits"], {"x": x_np})[0][0]
            inference_seconds = time.perf_counter() - started
            if not np.isfinite(logits_np).all():
                raise ValueError("Non-finite model output")
            shifted = logits_np - np.max(logits_np)
            probs = np.exp(shifted)
            probs /= np.sum(probs)
            top_indices = np.argsort(-probs, kind="stable")[:5]
            top5 = [
                {
                    "label": self.id_to_label[int(idx)],
                    "label_id": int(idx),
                    "score": float(probs[int(idx)]),
                }
                for idx in top_indices
            ]
        else:
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
            "inference_backend": self.runtime_backend,
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
        *,
        crop_rescue_enabled: bool = False,
    ) -> None:
        self.bundle = Path(bundle).resolve()
        self.low_confidence_threshold = float(low_confidence_threshold)
        self._vision = VisionExtractor(crop_rescue_enabled=crop_rescue_enabled)
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
        """Run extraction, normalization, and inference on a video file."""
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
        """Classify an in-memory segment slice through the video extraction path."""
        fps = _effective_fps(timestamps, fallback_fps=fallback_fps)
        clip_path = _write_temp_clip(frames, fps, prefer_compact=False)
        try:
            return self.classify_video(clip_path)
        finally:
            clip_path.unlink(missing_ok=True)
