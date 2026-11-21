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
    encode_frames_to_clip_bytes,
)


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
        timeout: float = 1.5,
        jpeg_quality: int = 70,
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
    ) -> tuple[list[list[float]], list[float]]:
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

        with self._lock:
            resp = self._client.post(
                f"{self.base_url}/api/vision/pose-frame",
                params={"session_id": session_id},
                content=buf.tobytes(),
                headers={"Content-Type": "image/jpeg"},
            )
            resp.raise_for_status()
            data = resp.json()
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
        fallback_threshold_seconds: float = 1.5,
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

    def classify_frames(
        self,
        frames: list[np.ndarray],
        timestamps: list[float],
        fallback_fps: float = 30.0,
    ) -> dict[str, Any]:
        clip_bytes, ext = encode_frames_to_clip_bytes(
            frames,
            timestamps,
            fallback_fps=fallback_fps,
            prefer_compact=True,
        )
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
            with self._lock:
                self._last_network_seconds = network_seconds
            return result

        assert self.bone_classifier is not None
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
        npz_bytes = resp.content
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
            qc=meta.get("qc", {}),
            inference_executor="pi_local",
            fallback_triggered=fallback_triggered,
        )
        return pred

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
