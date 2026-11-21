"""LAN Vision Backend (MediaPipe Pose + Extract + Fallback SL-GCN) for M2.2."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Any

import cv2
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

from deployment.m1.common import DEFAULT_BUNDLE
from deployment.m2.classifier import (
    BoneClassifier,
    VisionExtractor,
    decode_bundle_bytes_to_frames,
    serialize_landmark_arrays,
)
from deployment.m2.pipeline import _extract_pose_8

MAX_POSE_FRAME_BYTES = 4 * 1024 * 1024
MAX_CLIP_BYTES = 64 * 1024 * 1024
ALLOWED_CLIP_EXTENSIONS = {".avi", ".mp4", ".pbl6"}


class LivePoseRunner:
    """Thread-safe MediaPipe Pose holder with clean session resets for LAN frame streaming."""

    def __init__(self, pose_detector: Any = None) -> None:
        self._custom_detector = pose_detector
        self._mp_pose_instance: Any = None
        self._last_session_id: str | None = None
        self._lock = threading.Lock()

    def _close_unlocked(self) -> None:
        if self._mp_pose_instance is not None:
            close_fn = getattr(self._mp_pose_instance, "close", None)
            if callable(close_fn):
                try:
                    close_fn()
                except Exception:
                    pass
            self._mp_pose_instance = None

    def _ensure_pose_unlocked(self, session_id: str | None) -> Any:
        if self._custom_detector is not None:
            return self._custom_detector
        if session_id and self._last_session_id and session_id != self._last_session_id:
            self._close_unlocked()
        if self._mp_pose_instance is None:
            import mediapipe as mp

            self._mp_pose_instance = mp.solutions.pose.Pose(
                model_complexity=1,
                smooth_landmarks=False,
            )
        if session_id:
            self._last_session_id = session_id
        return self._mp_pose_instance

    def reset(self, session_id: str | None = None) -> None:
        with self._lock:
            self._close_unlocked()
            self._last_session_id = session_id

    def process_bgr(
        self,
        bgr: np.ndarray,
        session_id: str | None = None,
    ) -> tuple[list[list[float]], list[float], float]:
        started = time.perf_counter()
        with self._lock:
            detector = self._ensure_pose_unlocked(session_id)
            if self._custom_detector is not None and callable(detector):
                pose_8, vis_8 = detector(bgr, session_id or "")
            else:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                pose_res = detector.process(rgb)
                pose_8, vis_8 = _extract_pose_8(pose_res)
        return pose_8, vis_8, time.perf_counter() - started

    def close(self) -> None:
        with self._lock:
            self._close_unlocked()


async def _read_bounded_body(request: Request, max_bytes: int) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header") from error
        if declared > max_bytes:
            raise HTTPException(status_code=413, detail=f"Payload exceeds {max_bytes} byte limit")
    body = await request.body()
    if len(body) > max_bytes:
        raise HTTPException(status_code=413, detail=f"Payload exceeds {max_bytes} byte limit")
    if not body:
        raise HTTPException(status_code=400, detail="Request body is empty")
    return body


def _write_temp_bytes(body: bytes, ext: str) -> Path:
    fd, raw_path = tempfile.mkstemp(prefix="m2_vis_", suffix=ext)
    try:
        os.write(fd, body)
    finally:
        os.close(fd)
    return Path(raw_path)


def create_vision_app(
    bundle: Path = DEFAULT_BUNDLE,
    enable_fallback_classifier: bool = True,
    vision_extractor: VisionExtractor | None = None,
    bone_classifier: BoneClassifier | None = None,
    pose_detector: Any = None,
) -> FastAPI:
    extractor = vision_extractor or VisionExtractor()
    fallback_bone = bone_classifier
    if fallback_bone is None and enable_fallback_classifier:
        fallback_bone = BoneClassifier(bundle=bundle)
    pose_runner = LivePoseRunner(pose_detector=pose_detector)
    extract_lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            pose_runner.close()
            close_ext = getattr(extractor, "close", None)
            if callable(close_ext):
                close_ext()

    app = FastAPI(title="PBL6 SLR M2.2 Vision Backend", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.pose_runner = pose_runner
    app.state.extractor = extractor
    app.state.bone_classifier = fallback_bone

    def _run_extract_locked(clip_path: Path) -> tuple[dict[str, np.ndarray], dict[str, Any], bool, float]:
        with extract_lock:
            return extractor.extract_landmarks(clip_path)

    def _run_extract_bundle_locked(payload: bytes) -> tuple[dict[str, np.ndarray], dict[str, Any], bool, float]:
        frames, timestamps = decode_bundle_bytes_to_frames(payload)
        fn = getattr(extractor, "extract_from_frames", None)
        with extract_lock:
            if callable(fn):
                return fn(frames, timestamps)
            return extractor.extract_landmarks(Path("in_memory_bundle.pbl6"))

    async def _extract_from_request(
        request: Request,
        ext: str,
    ) -> tuple[dict[str, np.ndarray], dict[str, Any], bool, float]:
        clean_ext = ext.lower()
        if clean_ext not in ALLOWED_CLIP_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported clip extension; use .avi, .mp4, or .pbl6",
            )
        body = await _read_bounded_body(request, MAX_CLIP_BYTES)
        if clean_ext == ".pbl6":
            try:
                return await asyncio.to_thread(_run_extract_bundle_locked, body)
            except ValueError as error:
                raise HTTPException(status_code=400, detail=str(error)) from error
        tmp_path = _write_temp_bytes(body, clean_ext)
        try:
            return await asyncio.to_thread(_run_extract_locked, tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

    @app.get("/api/vision/health")
    def vision_health():
        return {
            "status": "ok",
            "schema_version": "m2.v1",
            "role": "vision_backend",
            "fallback_classifier_loaded": fallback_bone is not None,
            "model": dict(fallback_bone.identity) if fallback_bone is not None else None,
        }

    @app.post("/api/vision/pose-reset")
    def vision_pose_reset(session_id: str | None = None):
        pose_runner.reset(session_id=session_id)
        return {"ok": True, "session_id": session_id}

    @app.post("/api/vision/pose-frame")
    async def vision_pose_frame(request: Request, session_id: str | None = None):
        body = await _read_bounded_body(request, MAX_POSE_FRAME_BYTES)
        buf = np.frombuffer(body, dtype=np.uint8)
        bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if bgr is None:
            raise HTTPException(status_code=400, detail="Invalid encoded image frame")
        pose_8, vis_8, pose_s = await asyncio.to_thread(pose_runner.process_bgr, bgr, session_id)
        return {"pose": pose_8, "visibility": vis_8, "pose_seconds": pose_s}

    @app.post("/api/vision/extract-landmarks")
    async def vision_extract_landmarks(request: Request, ext: str = ".avi"):
        arrays, qc, crop_rescue, pre_s = await _extract_from_request(request, ext)
        npz_bytes = serialize_landmark_arrays(arrays)
        meta = {
            "preprocessing_seconds": pre_s,
            "crop_rescue": crop_rescue,
            "source_frames": int(len(arrays["xy"])),
            "landmark_payload_bytes": len(npz_bytes),
            "qc": qc,
        }
        return Response(
            content=npz_bytes,
            media_type="application/octet-stream",
            headers={"X-Vision-Meta": json.dumps(meta, ensure_ascii=True)},
        )

    @app.post("/api/vision/classify-clip")
    async def vision_classify_clip(request: Request, ext: str = ".avi"):
        if fallback_bone is None:
            raise HTTPException(status_code=503, detail="Fallback classifier is disabled on this backend")
        arrays, qc, crop_rescue, pre_s = await _extract_from_request(request, ext)
        result = await asyncio.to_thread(
            fallback_bone.infer_from_arrays,
            arrays,
            "backend_fallback",
        )
        result.update(
            schema_version="m2.v1",
            model=dict(fallback_bone.identity),
            preprocessing_seconds=pre_s,
            crop_rescue=crop_rescue,
            qc=qc,
        )
        return result

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PBL6 SLR M2.2 LAN Vision Backend")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument(
        "--no-fallback-classifier",
        action="store_true",
        help="Disable SL-GCN fallback classification endpoint (/api/vision/classify-clip)",
    )
    args = parser.parse_args()

    import uvicorn

    app = create_vision_app(
        bundle=args.bundle,
        enable_fallback_classifier=not args.no_fallback_classifier,
    )
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
