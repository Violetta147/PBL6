"""Non-blocking M2.1 live SLR session pipeline built directly on frozen M1 Segmenter."""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from dataclasses import asdict
import json
import math
import platform
import queue
import threading
import time
from pathlib import Path
from typing import Any, Callable
import uuid

import cv2
import numpy as np

from deployment.m1.common import ROOT
from deployment.m1.segmenter import Config, Segmenter, arm_states

SCHEMA_VERSION = "m2.v1"
FROZEN_CONFIG_PATH = ROOT / "deployment/m1/frozen-config.json"
POSE_SLOTS = (11, 12, 13, 14, 15, 16, 23, 24)


def load_frozen_config(path: Path = FROZEN_CONFIG_PATH) -> Config:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Config(**data)


class FrameRingBuffer:
    """Bounded timestamp-indexed ring buffer keeping pre-onset & active frames in RAM."""

    def __init__(self, max_seconds: float = 20.0) -> None:
        self.max_seconds = float(max_seconds)
        self._items: deque[tuple[float, np.ndarray]] = deque()
        self._lock = threading.Lock()

    def append(self, timestamp: float, frame: np.ndarray) -> None:
        with self._lock:
            self._items.append((timestamp, frame))
            cutoff = timestamp - self.max_seconds
            while len(self._items) > 1 and self._items[0][0] < cutoff:
                self._items.popleft()

    def slice(self, start: float, end: float) -> tuple[list[np.ndarray], list[float]]:
        with self._lock:
            frames: list[np.ndarray] = []
            timestamps: list[float] = []
            for ts, frame in self._items:
                if start <= ts <= end:
                    frames.append(frame.copy())
                    timestamps.append(ts)
            return frames, timestamps

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


def _extract_pose_8(pose_result: Any) -> tuple[list[list[float]], list[float]]:
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


class LiveSessionManager:
    """Coordinates live capture, M1 arms-down segmentation, FIFO 07b worker, and event broadcasts."""

    def __init__(
        self,
        classifier_fn: Callable[[list[np.ndarray], list[float]], dict[str, Any]],
        config: Config | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        max_queue_size: int = 16,
        ring_seconds: float = 20.0,
        pose_provider: Callable[[np.ndarray, str], tuple[list[list[float]], list[float]]] | None = None,
        on_capture_start: Callable[[str], None] | None = None,
    ) -> None:
        self._classifier_fn = classifier_fn
        self.config = config or load_frozen_config()
        self._on_event = on_event
        self._max_queue_size = max_queue_size
        self._ring_seconds = ring_seconds
        self._pose_provider = pose_provider
        self._on_capture_start = on_capture_start

        self._state_lock = threading.RLock()
        self._frame_lock = threading.RLock()
        self._latest_frame: np.ndarray | None = None

        self._epoch = 0
        self._event_seq = 0
        self._session_id: str | None = None
        self._running = False
        self._draining = False
        self._stop_event = threading.Event()

        self._segmenter = Segmenter(self.config)
        self._ring = FrameRingBuffer(max_seconds=ring_seconds)
        # Unbounded queue for tiny control events; heavy segment jobs are capped by _pending_segments.
        self._work_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._pending_segments = 0

        self._capture_thread: threading.Thread | None = None
        self._worker_thread: threading.Thread | None = None

        # Session history retained on screen after stop_session().
        self._arms: list[str | None] = [None, None]
        self._glosses: list[dict[str, Any]] = []
        self._utterances: list[dict[str, Any]] = []
        self._pending_utterance_items: dict[str, list[dict[str, Any]]] = {}
        self._closed_utterances: set[str] = set()
        self._incomplete_events: list[dict[str, Any]] = []
        self._last_error: str | None = None
        self._capture_open_event = threading.Event()
        self._capture_open_error: Exception | None = None
        self._last_status_emit = 0.0
        self._capture_fps = 0.0

    def _emit(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._state_lock:
            self._event_seq += 1
            event = {
                "schema_version": SCHEMA_VERSION,
                "event_id": f"{self._session_id or 'idle'}:{self._epoch}:{self._event_seq}",
                "session_id": self._session_id,
                "epoch": self._epoch,
                "type": event_type,
                "wall_time": time.time(),
                **payload,
            }
        if self._on_event is not None:
            try:
                self._on_event(event)
            except Exception:
                pass
        return event

    def get_latest_frame(self) -> np.ndarray | None:
        with self._frame_lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    def snapshot(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "schema_version": SCHEMA_VERSION,
                "session_id": self._session_id,
                "epoch": self._epoch,
                "running": self._running,
                "draining": self._draining,
                "segmenter_state": self._segmenter.state,
                "arms": list(self._arms),
                "queue_depth": self._pending_segments,
                "capture_fps": round(self._capture_fps, 1),
                "config": asdict(self.config),
                "glosses": list(self._glosses),
                "utterances": list(self._utterances),
                "incomplete_events": list(self._incomplete_events),
                "last_error": self._last_error,
            }

    def _reset_session_state(self) -> str:
        with self._state_lock:
            self._epoch += 1
            self._event_seq = 0
            self._session_id = f"live-{uuid.uuid4().hex[:10]}"
            self._running = True
            self._draining = False
            self._stop_event.clear()
            self._segmenter = Segmenter(self.config)
            self._ring = FrameRingBuffer(max_seconds=self._ring_seconds)
            self._work_queue = queue.Queue()
            self._pending_segments = 0
            self._arms = [None, None]
            self._glosses = []
            self._utterances = []
            self._pending_utterance_items = {}
            self._closed_utterances = set()
            self._incomplete_events = []
            self._last_error = None
            self._capture_open_event = threading.Event()
            self._capture_open_error = None
            self._capture_fps = 0.0
            return self._session_id

    def start_manual_session(self) -> str:
        """Start a session driven via feed_step() (used in unit tests & external frame feeders)."""
        if self._running or self._draining:
            raise RuntimeError("A session is already active or draining")
        session_id = self._reset_session_state()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(session_id, self._epoch),
            daemon=True,
            name="m2-classifier-worker",
        )
        self._worker_thread.start()
        self._emit("session_started", {"source": "manual", "config": asdict(self.config)})
        return session_id

    def start_camera_session(
        self,
        camera_index: int = 0,
        video_path: str | None = None,
        realtime_video: bool = True,
    ) -> str:
        """Start a live webcam or video-file session with non-blocking worker."""
        if self._running or self._draining:
            raise RuntimeError("A session is already active or draining")
        session_id = self._reset_session_state()
        epoch = self._epoch

        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            args=(session_id, epoch),
            daemon=True,
            name="m2-classifier-worker",
        )
        self._worker_thread.start()

        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            args=(session_id, epoch, camera_index, video_path, realtime_video),
            daemon=True,
            name="m2-capture-pose",
        )
        self._capture_thread.start()
        self._capture_open_event.wait(timeout=3.0)
        if self._capture_open_error is not None:
            err = self._capture_open_error
            self.stop_session(wait_timeout=1.0)
            with self._state_lock:
                self._last_error = str(err)
            raise ValueError(str(err))
        self._emit(
            "session_started",
            {
                "source": "video" if video_path else f"camera:{camera_index}",
                "config": asdict(self.config),
            },
        )
        return session_id

    def feed_step(
        self,
        timestamp: float,
        arms: list[str | None],
        frame: np.ndarray | None = None,
    ) -> list[dict[str, Any]]:
        """Feed one strictly-increasing timestamped observation into M1 Segmenter."""
        if not self._running:
            return []
        if frame is not None:
            self._ring.append(timestamp, frame)
            with self._frame_lock:
                self._latest_frame = frame

        prev_state = self._segmenter.state
        events = self._segmenter.feed(timestamp, arms)
        with self._state_lock:
            self._arms = list(arms)
            new_state = self._segmenter.state

        now = time.perf_counter()
        if new_state != prev_state or (now - self._last_status_emit) >= 0.25:
            self._last_status_emit = now
            self._emit(
                "status",
                {
                    "segmenter_state": new_state,
                    "arms": list(arms),
                    "timestamp": timestamp,
                    "queue_depth": self._pending_segments,
                    "capture_fps": round(self._capture_fps, 1),
                },
            )

        for ev in events:
            self._handle_segmenter_event(ev, timestamp)
        return events

    def _handle_segmenter_event(self, ev: dict[str, Any], wall_ts: float) -> None:
        if ev.get("type") == "utterance_end":
            self._enqueue_work({"kind": "utterance_end", "utterance_id": ev["utterance_id"], "timestamp": ev["timestamp"]})
            return

        status = ev.get("status")
        if status == "complete":
            frames, timestamps = self._ring.slice(ev["start"], ev["end"])
            if not frames:
                incomplete = {**ev, "status": "incomplete", "reason": "empty_buffer_slice"}
                with self._state_lock:
                    self._incomplete_events.append(incomplete)
                self._emit("segment_incomplete", {"segment": incomplete})
                return

            self._emit("segment_complete", {"segment": ev, "frame_count": len(frames)})
            self._enqueue_work(
                {
                    "kind": "segment",
                    "segment": ev,
                    "frames": frames,
                    "timestamps": timestamps,
                    "enqueued_at": time.perf_counter(),
                }
            )
        elif status == "incomplete":
            with self._state_lock:
                self._incomplete_events.append(ev)
            self._emit("segment_incomplete", {"segment": ev})

    def _enqueue_work(self, item: dict[str, Any]) -> None:
        if item.get("kind") == "segment":
            with self._state_lock:
                if self._pending_segments >= self._max_queue_size:
                    seg = {**item["segment"], "status": "incomplete", "reason": "queue_overflow"}
                    self._incomplete_events.append(seg)
                    overflow = seg
                else:
                    self._pending_segments += 1
                    overflow = None
            if overflow is not None:
                self._emit("segment_incomplete", {"segment": overflow})
                return
        self._work_queue.put_nowait(item)

    def stop_session(self, wait_timeout: float = 120.0) -> dict[str, Any]:
        """Stop capturing, mark open movement incomplete, drain already-completed segments, keep history."""
        with self._state_lock:
            if not self._running and not self._draining:
                return self.snapshot()
            self._running = False
            self._draining = True
            self._stop_event.set()
            capture_thread = self._capture_thread
            worker_thread = self._worker_thread

        if capture_thread is not None and capture_thread.is_alive() and capture_thread is not threading.current_thread():
            capture_thread.join(timeout=5.0)

        # Mark any open movement incomplete (end_of_file), keeping already-queued completed segments.
        for ev in self._segmenter.finish():
            self._handle_segmenter_event(ev, self._segmenter.last or 0.0)

        # Push deterministic end sentinel so FIFO worker drains all queued segments first.
        self._work_queue.put({"kind": "session_end", "timestamp": self._segmenter.last or 0.0})

        if worker_thread is not None and worker_thread.is_alive() and worker_thread is not threading.current_thread():
            worker_thread.join(timeout=wait_timeout)

        with self._state_lock:
            self._draining = False
            self._capture_thread = None
            self._worker_thread = None

        self._emit("session_stopped", {"snapshot": self.snapshot()})
        return self.snapshot()

    def _discover_linux_video_nodes(self) -> tuple[list[int], list[str]]:
        dev_dir = Path("/dev")
        if not dev_dir.is_dir():
            return [], []
        indices: list[int] = []
        nodes: list[str] = []
        for entry in sorted(dev_dir.glob("video*")):
            suffix = entry.name[5:]
            if suffix.isdigit():
                idx = int(suffix)
                if 0 <= idx <= 9:
                    indices.append(idx)
                    nodes.append(str(entry))
        return indices, nodes

    def _open_capture(self, camera_index: int, video_path: str | None) -> cv2.VideoCapture:
        if video_path:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise ValueError(f"Cannot open video source: {video_path}")
            return cap
        if platform.system() == "Windows":
            cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
            if cap.isOpened():
                return cap
            cap.release()
        if platform.system() == "Linux":
            dev_indices, usb_nodes = self._discover_linux_video_nodes()
            candidates: list[int] = []
            for idx in (int(camera_index), 0, 1, 2, 3, *dev_indices):
                if idx >= 0 and idx not in candidates:
                    candidates.append(idx)
            v4l2_backend = getattr(cv2, "CAP_V4L2", None)
            backends: tuple[int | None, ...] = (v4l2_backend, None) if v4l2_backend is not None else (None,)
            for idx in candidates:
                for backend in backends:
                    cap = cv2.VideoCapture(idx, backend) if backend is not None else cv2.VideoCapture(idx)
                    if not cap.isOpened():
                        cap.release()
                        continue
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    ok, frame = cap.read()
                    if ok and frame is not None and getattr(frame, "size", 0) > 0:
                        with self._frame_lock:
                            self._latest_frame = frame.copy()
                        return cap
                    cap.release()
            if not usb_nodes:
                raise ValueError(
                    "Không tìm thấy USB camera trên Pi (/dev/video0..9 trống) — hãy kiểm tra cáp USB camera."
                )
            raise ValueError(
                f"Không mở được USB camera trên Pi (đã thử V4L2 index {candidates}; thiết bị hiện có: {usb_nodes})."
            )
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            raise ValueError(f"Cannot open camera index {camera_index}")
        return cap

    @contextmanager
    def _pose_context(self, session_id: str):
        if self._pose_provider is not None:
            if self._on_capture_start is not None:
                try:
                    self._on_capture_start(session_id)
                except Exception as exc:
                    msg = f"Không kết nối được Vision Backend ({exc}) — đang hiển thị Camera trực tiếp."
                    with self._state_lock:
                        self._last_error = msg
                    self._emit("error", {"message": msg})
            yield lambda bgr: self._pose_provider(bgr, session_id)
            return
        import mediapipe as mp

        with mp.solutions.pose.Pose(model_complexity=1, smooth_landmarks=False) as pose_model:
            def _local_pose(bgr: np.ndarray) -> tuple[list[list[float]], list[float]]:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                pose_res = pose_model.process(rgb)
                return _extract_pose_8(pose_res)

            yield _local_pose

    def _capture_loop(
        self,
        session_id: str,
        epoch: int,
        camera_index: int,
        video_path: str | None,
        realtime_video: bool,
    ) -> None:
        cap = None
        try:
            cap = self._open_capture(camera_index, video_path)
            self._capture_open_event.set()
            if not video_path:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_FPS, 30)

            video_fps = cap.get(cv2.CAP_PROP_FPS)
            if not np.isfinite(video_fps) or video_fps <= 0:
                video_fps = 30.0

            t0 = time.perf_counter()
            last_ts = -1.0
            fps_window: deque[float] = deque(maxlen=30)

            with self._pose_context(session_id) as estimate_pose:
                frame_idx = 0
                last_pose_err_emit = -10.0
                while not self._stop_event.is_set():
                    ok, bgr = cap.read()
                    if not ok:
                        if video_path:
                            break
                        time.sleep(0.01)
                        continue

                    with self._frame_lock:
                        self._latest_frame = bgr.copy()

                    now = time.perf_counter()
                    fps_window.append(now)
                    if len(fps_window) >= 2 and fps_window[-1] > fps_window[0]:
                        self._capture_fps = (len(fps_window) - 1) / (fps_window[-1] - fps_window[0])

                    if video_path:
                        pos_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
                        ts = (pos_msec / 1000.0) if (np.isfinite(pos_msec) and pos_msec >= 0) else (frame_idx / video_fps)
                        if ts <= last_ts:
                            ts = last_ts + (1.0 / video_fps)
                    else:
                        ts = now - t0
                        if ts <= last_ts:
                            ts = last_ts + 1e-4
                    last_ts = ts
                    frame_idx += 1

                    try:
                        pose, visibility = estimate_pose(bgr)
                        arms = arm_states(pose, visibility, self.config)
                        with self._state_lock:
                            if self._last_error and self._last_error.startswith("Không kết nối được Vision Backend"):
                                self._last_error = None
                    except Exception as exc:
                        arms = [None, None]
                        now_err = time.perf_counter()
                        if now_err - last_pose_err_emit >= 5.0:
                            last_pose_err_emit = now_err
                            err_msg = (
                                "Không kết nối được Vision Backend trên Laptop (192.168.1.155:8767) "
                                f"— hãy mở Firewall cổng 8767 trên Windows ({exc})."
                            )
                            with self._state_lock:
                                self._last_error = err_msg
                            self._emit("error", {"message": err_msg})

                    self.feed_step(ts, arms, frame=bgr)

                    if video_path and realtime_video:
                        target_wall = t0 + ts
                        sleep_s = target_wall - time.perf_counter()
                        if sleep_s > 0:
                            time.sleep(min(sleep_s, 0.1))
        except Exception as error:
            if not self._capture_open_event.is_set():
                self._capture_open_error = error
                self._capture_open_event.set()
            with self._state_lock:
                self._last_error = str(error)
            self._emit("error", {"message": str(error)})
        finally:
            if cap is not None:
                cap.release()
            # Ensure failed or finished capture loops never leave a zombie running=True session.
            if self._running and self._capture_open_error is None:
                threading.Thread(target=self.stop_session, daemon=True, name="m2-auto-stop").start()

    def _finalize_utterance(self, utterance_id: str, timestamp: float, reason: str) -> None:
        with self._state_lock:
            if utterance_id in self._closed_utterances:
                return
            items = self._pending_utterance_items.pop(utterance_id, [])
            if not items:
                return
            self._closed_utterances.add(utterance_id)
            utterance = {
                "utterance_id": utterance_id,
                "revision": 1,
                "reason": reason,
                "timestamp": timestamp,
                "raw_glosses": [item["raw"]["top1_label"] for item in items],
                "segments": items,
                "revised_glosses": None,
                "vietnamese_sentence": None,
            }
            self._utterances.append(utterance)
        self._emit("utterance_ready", {"utterance": utterance})

    def _worker_loop(self, session_id: str, epoch: int) -> None:
        while True:
            item = self._work_queue.get()
            kind = item.get("kind")
            try:
                if kind == "segment":
                    seg = item["segment"]
                    pred = self._classifier_fn(item["frames"], item["timestamps"])
                    end_to_display = time.perf_counter() - item["enqueued_at"]
                    record = {
                        "segment_id": seg["segment_id"],
                        "utterance_id": seg["utterance_id"],
                        "start": seg["start"],
                        "movement_start": seg["movement_start"],
                        "movement_end": seg["movement_end"],
                        "end": seg["end"],
                        "raw": {
                            "top1_label": pred["top1_label"],
                            "top1_id": pred["top1_id"],
                            "confidence": pred["confidence"],
                            "low_confidence": pred["low_confidence"],
                            "top5": pred["top5"],
                        },
                        "timing": {
                            "preprocessing_seconds": pred.get("preprocessing_seconds", 0.0),
                            "inference_seconds": pred.get("inference_seconds", 0.0),
                            "network_seconds": pred.get("network_seconds", 0.0),
                            "queue_and_classify_seconds": end_to_display,
                        },
                        "executor": pred.get("inference_executor", "local"),
                        "source_frames": pred.get("source_frames", len(item["frames"])),
                    }
                    if "landmark_payload_bytes" in pred:
                        record["landmark_payload_bytes"] = pred["landmark_payload_bytes"]
                    with self._state_lock:
                        self._glosses.append(record)
                        self._pending_utterance_items.setdefault(seg["utterance_id"], []).append(record)
                    self._emit("gloss_result", {"gloss": record})

                elif kind == "utterance_end":
                    self._finalize_utterance(item["utterance_id"], item["timestamp"], reason="utterance_rest")

                elif kind == "session_end":
                    # Flush any remaining open utterance(s) that already have completed segments.
                    with self._state_lock:
                        remaining_ids = sorted(self._pending_utterance_items.keys(), key=lambda x: int(x))
                    for uid in remaining_ids:
                        self._finalize_utterance(uid, item.get("timestamp", 0.0), reason="session_stop")
                    break
            except Exception as error:
                with self._state_lock:
                    self._last_error = f"Classifier error: {error}"
                self._emit("error", {"message": f"Classifier error: {error}", "segment": item.get("segment")})
            finally:
                if kind == "segment":
                    with self._state_lock:
                        self._pending_segments = max(0, self._pending_segments - 1)
                self._work_queue.task_done()
