"""FastAPI + WebSocket server for M2.1 local & M2.2 Pi-split VSL400 recognition."""
from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
from typing import Any

import cv2
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import numpy as np
from pydantic import BaseModel

from deployment.m1.common import DEFAULT_BUNDLE, ROOT
from deployment.m2.classifier import BoneClassifier, SLRClassifier
from deployment.m2.pipeline import LiveSessionManager
from deployment.m2.remote_clients import RemotePoseClient, SplitClassifierClient

INDEX_HTML = Path(__file__).with_name("index.html")
DEFAULT_TTS_DIR = ROOT.parent / "slr-app" / "MVP" / "local_data" / "tts"


class StartSessionRequest(BaseModel):
    camera_index: int = 0
    video_path: str | None = None
    realtime_video: bool = True


class RuntimeFallbackRequest(BaseModel):
    fallback_active: bool
    reason: str | None = None


class WebSocketHub:
    """Thread-safe fan-out hub broadcasting M2 events to Pi UI & Companion browsers."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    @property
    def client_count(self) -> int:
        return len(self._clients)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self._clients:
            return
        payload = json.dumps(message, ensure_ascii=False)
        dead: list[WebSocket] = []
        for ws in list(self._clients):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)

    def publish_from_thread(self, message: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        loop.call_soon_threadsafe(lambda: asyncio.create_task(self.broadcast(message)))


def _make_idle_jpeg() -> bytes:
    img = np.full((480, 640, 3), 245, dtype=np.uint8)
    cv2.putText(
        img,
        "CAMERA IDLE - Click Start Session",
        (95, 245),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (79, 93, 107),
        2,
        cv2.LINE_AA,
    )
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    return buf.tobytes() if ok else b""


def _build_runtime(
    *,
    bundle: Path,
    classifier: SLRClassifier | None,
    classifier_fn: Any,
    preload_model: bool,
    inference_mode: str,
    vision_backend_url: str | None,
    fallback_threshold_seconds: float,
    pose_provider: Any,
    on_capture_start: Any,
    runtime_controller: Any,
) -> dict[str, Any]:
    if inference_mode not in ("local", "pi-split", "remote-fallback"):
        raise ValueError(f"Unsupported inference_mode: {inference_mode}")

    remote_pose: RemotePoseClient | None = None
    split_client: SplitClassifierClient | None = None

    if classifier_fn is not None:
        return {
            "fn": classifier_fn,
            "model_identity": {"bundle": "injected-test-classifier"},
            "pose_provider": pose_provider,
            "on_capture_start": on_capture_start,
            "controller": runtime_controller,
            "closables": [],
        }

    if inference_mode in ("pi-split", "remote-fallback"):
        if not vision_backend_url:
            raise ValueError(f"vision_backend_url is required when inference_mode={inference_mode!r}")
        closables: list[Any] = []
        if pose_provider is None:
            remote_pose = RemotePoseClient(vision_backend_url)
            closables.append(remote_pose)
            pose_provider = remote_pose.detect_pose_8
            if on_capture_start is None:
                on_capture_start = remote_pose.reset

        if isinstance(runtime_controller, SplitClassifierClient):
            split_client = runtime_controller
            model_identity = (
                dict(split_client.bone_classifier.identity)
                if split_client.bone_classifier is not None
                else {"bundle": "remote-vision-backend", "vision_backend_url": vision_backend_url}
            )
        elif inference_mode == "pi-split":
            bone = BoneClassifier(bundle=bundle)
            split_client = SplitClassifierClient(
                vision_backend_url,
                bone_classifier=bone,
                mode="pi-split",
                fallback_threshold_seconds=fallback_threshold_seconds,
            )
            closables.append(split_client)
            model_identity = dict(bone.identity)
        else:
            split_client = SplitClassifierClient(
                vision_backend_url,
                bone_classifier=None,
                mode="remote-fallback",
                fallback_threshold_seconds=fallback_threshold_seconds,
            )
            closables.append(split_client)
            model_identity = {"bundle": "remote-vision-backend", "vision_backend_url": vision_backend_url}

        return {
            "fn": split_client.classify_frames,
            "model_identity": model_identity,
            "pose_provider": pose_provider,
            "on_capture_start": on_capture_start,
            "controller": split_client,
            "closables": closables,
        }

    loaded_classifier = classifier
    if loaded_classifier is None and preload_model:
        loaded_classifier = SLRClassifier(bundle=bundle)
    if loaded_classifier is None:
        raise ValueError("Either classifier, classifier_fn, or preload_model=True is required")

    return {
        "fn": loaded_classifier.classify_frames,
        "model_identity": dict(loaded_classifier.identity),
        "pose_provider": pose_provider,
        "on_capture_start": on_capture_start,
        "controller": runtime_controller,
        "closables": [],
    }


def create_app(
    bundle: Path = DEFAULT_BUNDLE,
    classifier: SLRClassifier | None = None,
    classifier_fn: Any = None,
    preload_model: bool = True,
    tts_dir: Path = DEFAULT_TTS_DIR,
    inference_mode: str = "local",
    vision_backend_url: str | None = None,
    fallback_threshold_seconds: float = 1.5,
    pose_provider: Any = None,
    on_capture_start: Any = None,
    runtime_controller: Any = None,
) -> FastAPI:
    hub = WebSocketHub()
    rt = _build_runtime(
        bundle=bundle,
        classifier=classifier,
        classifier_fn=classifier_fn,
        preload_model=preload_model,
        inference_mode=inference_mode,
        vision_backend_url=vision_backend_url,
        fallback_threshold_seconds=fallback_threshold_seconds,
        pose_provider=pose_provider,
        on_capture_start=on_capture_start,
        runtime_controller=runtime_controller,
    )
    model_identity = rt["model_identity"]
    controller = rt["controller"]

    manager = LiveSessionManager(
        classifier_fn=rt["fn"],
        on_event=hub.publish_from_thread,
        pose_provider=rt["pose_provider"],
        on_capture_start=rt["on_capture_start"],
    )
    idle_jpeg = _make_idle_jpeg()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        hub.bind_loop(asyncio.get_running_loop())
        try:
            yield
        finally:
            snap = manager.snapshot()
            if snap["running"] or snap["draining"]:
                manager.stop_session(10.0)
            for client in rt["closables"]:
                try:
                    client.close()
                except Exception:
                    pass

    app = FastAPI(title="PBL6 SLR Live Server", version="0.2.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.manager = manager
    app.state.hub = hub
    app.state.runtime_controller = controller

    def _runtime_status() -> dict[str, Any]:
        if controller is not None:
            return controller.status()
        return {
            "inference_mode": inference_mode,
            "active_executor": "local",
            "fallback_active": False,
            "fallback_reason": None,
            "fallback_threshold_seconds": float(fallback_threshold_seconds),
            "vision_backend_url": vision_backend_url,
        }

    @app.get("/")
    def index():
        return FileResponse(INDEX_HTML)

    @app.get("/api/health")
    def health():
        snap = manager.snapshot()
        return {
            "status": "ok",
            "schema_version": snap["schema_version"],
            "model": model_identity,
            "running": snap["running"],
            "draining": snap["draining"],
            "ws_clients": hub.client_count,
            "runtime": _runtime_status(),
        }

    @app.get("/api/state")
    def state():
        return manager.snapshot()

    @app.post("/api/runtime/fallback")
    def runtime_fallback(req: RuntimeFallbackRequest):
        if controller is None:
            raise HTTPException(
                status_code=400,
                detail="Runtime fallback toggle is only available in pi-split or remote-fallback mode",
            )
        try:
            updated = controller.set_fallback(req.fallback_active, reason=req.reason)
            return {"ok": True, "runtime": updated}
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    resolved_tts_dir = Path(tts_dir).resolve()

    @app.get("/api/tts/{label_id}.mp3")
    def tts_audio(label_id: int):
        if label_id < 0 or label_id >= 400:
            raise HTTPException(status_code=404, detail="TTS label out of range")
        audio_path = (resolved_tts_dir / f"{label_id}.mp3").resolve()
        if not audio_path.is_relative_to(resolved_tts_dir) or not audio_path.is_file():
            raise HTTPException(status_code=404, detail="TTS audio not found")
        return FileResponse(audio_path, media_type="audio/mpeg")

    @app.post("/api/session/start")
    async def session_start(req: StartSessionRequest | None = None):
        payload = req or StartSessionRequest()
        try:
            session_id = await asyncio.to_thread(
                manager.start_camera_session,
                payload.camera_index,
                payload.video_path,
                payload.realtime_video,
            )
            return {"ok": True, "session_id": session_id, "state": manager.snapshot()}
        except (RuntimeError, ValueError) as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post("/api/session/stop")
    async def session_stop():
        snap = await asyncio.to_thread(manager.stop_session, 120.0)
        return {"ok": True, "state": snap}

    @app.get("/video_feed")
    async def video_feed():
        async def generate():
            while True:
                frame = manager.get_latest_frame()
                if frame is not None:
                    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                    jpg = encoded.tobytes() if ok else idle_jpeg
                else:
                    jpg = idle_jpeg
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
                )
                await asyncio.sleep(0.05)

        return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

    @app.websocket("/ws/live")
    async def ws_live(websocket: WebSocket):
        await hub.connect(websocket)
        try:
            await websocket.send_text(
                json.dumps({"type": "snapshot", "snapshot": manager.snapshot()}, ensure_ascii=False)
            )
            while True:
                # Keep connection alive; ignore client ping/text payloads.
                await websocket.receive_text()
        except WebSocketDisconnect:
            hub.disconnect(websocket)
        except Exception:
            hub.disconnect(websocket)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PBL6 SLR Live Server (M2.1 local / M2.2 split)")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument(
        "--inference-mode",
        choices=("local", "pi-split", "remote-fallback"),
        default="local",
    )
    parser.add_argument("--vision-backend-url", default=None)
    parser.add_argument("--fallback-threshold", type=float, default=1.5)
    parser.add_argument("--tts-dir", type=Path, default=DEFAULT_TTS_DIR)
    args = parser.parse_args()

    import uvicorn

    app = create_app(
        bundle=args.bundle,
        preload_model=True,
        tts_dir=args.tts_dir,
        inference_mode=args.inference_mode,
        vision_backend_url=args.vision_backend_url,
        fallback_threshold_seconds=args.fallback_threshold,
    )
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
