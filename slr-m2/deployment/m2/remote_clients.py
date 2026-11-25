"""Pi 4B Edge remote clients talking to the M2.2 LAN Vision Backend."""
from __future__ import annotations

import json
import threading
import time
from typing import Any

import cv2
import httpx
import numpy as np

from deployment.m2.classifier import (
    BoneClassifier,
    deserialize_landmark_arrays,
    encode_frames_to_bundle_bytes,
)

DEFAULT_FALLBACK_THRESHOLD_SECONDS = 0.0


def _clean_base_url(base_url: str) -> str:
    clean = base_url.strip().rstrip("/")
    if not clean:
        raise ValueError("vision_backend_url must not be empty")
    return clean


class RemotePoseClient:
    """Streams capture frames to LAN Vision Backend /api/vision/pose-frame over keep-alive HTTP."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 2.5,
        jpeg_quality: int = 75,
        max_width: int = 640,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = _clean_base_url(base_url)
        self.jpeg_quality = int(jpeg_quality)
        self.max_width = int(max_width)
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)
        self._lock = threading.Lock()

    def reset(self, session_id: str) -> None:
        try:
            with self._lock:
                self._client.post(
                    f"{self.base_url}/api/vision/pose-reset",
                    params={"session_id": session_id},
                )
        except Exception:
            pass

    def detect_pose_8(
        self,
        bgr: np.ndarray,
        session_id: str,
        *,
        ts: float | None = None,
        seq: int | None = None,
        run_hands: bool = False,
        timing: dict[str, Any] | None = None,
    ) -> tuple[list[list[float]], list[float]]:
        if timing is not None:
            encode_started = time.perf_counter()
        frame = bgr
        if self.max_width > 0 and frame.shape[1] > self.max_width:
            scale = self.max_width / float(frame.shape[1])
            new_h = max(1, int(round(frame.shape[0] * scale)))
            frame = cv2.resize(frame, (self.max_width, new_h), interpolation=cv2.INTER_AREA)

        ok, buf = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality],
        )
        if not ok:
            raise RuntimeError("Failed to JPEG-encode frame for remote pose estimation")

        payload = buf.tobytes()
        params: dict[str, Any] = {"session_id": session_id}
        if timing is not None:
            timing["encode_ms"] = (time.perf_counter() - encode_started) * 1000
            timing["jpeg_bytes"] = len(payload)
            params["measure"] = 1
        if ts is not None and seq is not None:
            params["ts"] = float(ts)
            params["seq"] = int(seq)
            params["run_hands"] = 1 if run_hands else 0

        with self._lock:
            if timing is not None:
                timing["send_at"] = time.perf_counter()
            try:
                resp = self._client.post(
                    f"{self.base_url}/api/vision/pose-frame",
                    params=params,
                    content=payload,
                    headers={"Content-Type": "image/jpeg"},
                )
            finally:
                if timing is not None:
                    finished = time.perf_counter()
                    timing["http_ms"] = (finished - timing["send_at"]) * 1000
            if timing is not None:
                timing["response_at"] = finished
                timing["http_status"] = resp.status_code
                timing["frame_age_ms"] = (finished - timing["captured_at"]) * 1000
            resp.raise_for_status()
            data = resp.json()
        if timing is not None:
            vision = data.get("timing_ms", {})
            for key in ("handler", "body_read", "decode", "worker_wait", "mediapipe_lock_wait", "mediapipe"):
                duration_ms = vision.get(key)
                if isinstance(duration_ms, (int, float)):
                    timing[f"laptop_{key}_ms"] = duration_ms
            pose_seconds = data.get("pose_seconds")
            if isinstance(pose_seconds, (int, float)):
                timing["laptop_pose_total_ms"] = pose_seconds * 1000
        return data["pose"], data["visibility"]

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


class SplitClassifierClient:
    """Runs Stage A on LAN Vision Backend and Stage B on Pi (with automatic slow-forward fallback)."""

    def __init__(
        self,
        vision_backend_url: str,
        bone_classifier: BoneClassifier | None = None,
        mode: str = "pi-split",
        fallback_threshold_seconds: float = DEFAULT_FALLBACK_THRESHOLD_SECONDS,
        consecutive_slow_limit: int = 2,
        timeout: float = 120.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        if mode not in ("pi-split", "remote-fallback"):
            raise ValueError(f"Unsupported split mode: {mode}")
        if mode == "pi-split" and bone_classifier is None:
            raise ValueError("pi-split mode requires a local BoneClassifier instance")
        if consecutive_slow_limit < 1:
            raise ValueError("consecutive_slow_limit must be >= 1")

        self.vision_backend_url = _clean_base_url(vision_backend_url)
        self.bone_classifier = bone_classifier
        self.mode = mode
        self.fallback_threshold_seconds = float(fallback_threshold_seconds)
        self.consecutive_slow_limit = int(consecutive_slow_limit)
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=timeout)

        self._lock = threading.Lock()
        self._fallback_active = mode == "remote-fallback"
        self._consecutive_slow = 0
        self._fallback_reason: str | None = (
            "Configured in remote-fallback mode" if self._fallback_active else None
        )
        self._last_pi_inference_seconds: float | None = None
        self._last_network_seconds: float | None = None
        self._last_payload_bytes: int | None = None

    def set_fallback(self, active: bool, reason: str | None = None) -> dict[str, Any]:
        with self._lock:
            if not active and self.bone_classifier is None:
                raise ValueError("Cannot disable fallback without a local BoneClassifier")
            self._fallback_active = bool(active)
            self._consecutive_slow = 0
            if self._fallback_active:
                self._fallback_reason = reason or "Manual backend fallback enabled"
            else:
                self._fallback_reason = None
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "inference_mode": self.mode,
                "active_executor": "backend_fallback" if self._fallback_active else "pi_local",
                "fallback_active": self._fallback_active,
                "fallback_reason": self._fallback_reason,
                "fallback_threshold_seconds": self.fallback_threshold_seconds,
                "consecutive_slow_limit": self.consecutive_slow_limit,
                "consecutive_slow": self._consecutive_slow,
                "last_pi_inference_seconds": self._last_pi_inference_seconds,
                "last_network_seconds": self._last_network_seconds,
                "last_payload_bytes": self._last_payload_bytes,
                "vision_backend_url": self.vision_backend_url,
            }

    def _finish_pi_local(
        self,
        npz_bytes: bytes,
        meta: dict[str, Any],
        network_seconds: float,
        *,
        streaming_used: bool,
    ) -> dict[str, Any]:
        assert self.bone_classifier is not None
        arrays = deserialize_landmark_arrays(npz_bytes)
        pred = self.bone_classifier.infer_from_arrays(arrays, inference_executor="pi_local")
        inference_seconds = float(pred["inference_seconds"])

        fallback_triggered = False
        with self._lock:
            self._last_pi_inference_seconds = inference_seconds
            self._last_network_seconds = network_seconds
            self._last_payload_bytes = len(npz_bytes)
            if self.fallback_threshold_seconds > 0 and inference_seconds > self.fallback_threshold_seconds:
                self._consecutive_slow += 1
                if not self._fallback_active and self._consecutive_slow >= self.consecutive_slow_limit:
                    self._fallback_active = True
                    self._fallback_reason = (
                        f"Pi SL-GCN forward {inference_seconds:.3f}s > "
                        f"{self.fallback_threshold_seconds:.2f}s ({self.consecutive_slow_limit}x consecutive)"
                    )
                    fallback_triggered = True
            else:
                self._consecutive_slow = 0

        pred.update(
            schema_version="m2.v1",
            model=dict(self.bone_classifier.identity),
            preprocessing_seconds=float(meta.get("preprocessing_seconds", 0.0)),
            network_seconds=network_seconds,
            landmark_payload_bytes=len(npz_bytes),
            crop_rescue=bool(meta.get("crop_rescue", False)),
            streaming_used=streaming_used,
            catchup_hands_frames=int(meta.get("catchup_hands_frames", 0)),
            qc=meta.get("qc", {}),
            inference_executor="pi_local",
            fallback_triggered=fallback_triggered,
        )
        return pred

    def classify_segment(
        self,
        frames: list[np.ndarray],
        timestamps: list[float],
        *,
        session_id: str | None = None,
        start: float | None = None,
        end: float | None = None,
        target_seq: int | None = None,
        fallback_fps: float = 30.0,
    ) -> dict[str, Any]:
        """Classify a closed segment via Laptop RAM stream slice, falling back cleanly to .pbl6."""
        if not session_id or start is None or end is None:
            return self.classify_frames(frames, timestamps, fallback_fps=fallback_fps)

        with self._lock:
            use_fallback = self._fallback_active or self.bone_classifier is None

        payload = {
            "session_id": session_id,
            "start": float(start),
            "end": float(end),
            "target_seq": target_seq,
        }
        started = time.perf_counter()
        try:
            if use_fallback:
                resp = self._client.post(
                    f"{self.vision_backend_url}/api/vision/classify-segment",
                    json=payload,
                )
                resp.raise_for_status()
                network_seconds = time.perf_counter() - started
                result = resp.json()
                result["network_seconds"] = network_seconds
                result["inference_executor"] = "backend_fallback"
                result["streaming_used"] = bool(result.get("streaming_used", True))
                with self._lock:
                    self._last_network_seconds = network_seconds
                return result

            resp = self._client.post(
                f"{self.vision_backend_url}/api/vision/extract-segment",
                json=payload,
            )
            resp.raise_for_status()
            network_seconds = time.perf_counter() - started
            meta = json.loads(resp.headers.get("X-Vision-Meta", "{}"))
            return self._finish_pi_local(
                resp.content,
                meta,
                network_seconds,
                streaming_used=bool(meta.get("streaming_used", True)),
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (404, 405):
                return self.classify_frames(frames, timestamps, fallback_fps=fallback_fps)
            raise

    def classify_frames(
        self,
        frames: list[np.ndarray],
        timestamps: list[float],
        fallback_fps: float = 30.0,
    ) -> dict[str, Any]:
        clip_bytes = encode_frames_to_bundle_bytes(frames, timestamps)
        ext = ".pbl6"
        with self._lock:
            use_fallback = self._fallback_active or self.bone_classifier is None

        if use_fallback:
            started = time.perf_counter()
            resp = self._client.post(
                f"{self.vision_backend_url}/api/vision/classify-clip",
                params={"ext": ext},
                content=clip_bytes,
                headers={"Content-Type": "application/octet-stream"},
            )
            resp.raise_for_status()
            network_seconds = time.perf_counter() - started
            result = resp.json()
            result["network_seconds"] = network_seconds
            result["inference_executor"] = "backend_fallback"
            result["streaming_used"] = False
            with self._lock:
                self._last_network_seconds = network_seconds
            return result

        started = time.perf_counter()
        resp = self._client.post(
            f"{self.vision_backend_url}/api/vision/extract-landmarks",
            params={"ext": ext},
            content=clip_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )
        resp.raise_for_status()
        network_seconds = time.perf_counter() - started
        meta = json.loads(resp.headers.get("X-Vision-Meta", "{}"))
        return self._finish_pi_local(resp.content, meta, network_seconds, streaming_used=False)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
