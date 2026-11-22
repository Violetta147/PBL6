"""Non-blocking M2.1 live SLR session pipeline built directly on frozen M1 Segmenter."""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from dataclasses import asdict, replace
import inspect
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
from deployment.m2.classifier import POSE_SLOTS, extract_pose_8

SCHEMA_VERSION = "m2.v1"
FROZEN_CONFIG_PATH = ROOT / "deployment/m1/frozen-config.json"
DEFAULT_UTTERANCE_REST_SECONDS = 4.0
UTTERANCE_TRACKING_GRACE_SECONDS = 0.5
TIMESTAMP_TOLERANCE = 1e-9
MAX_PENDING_POSE_FRAMES = 32
_extract_pose_8 = extract_pose_8


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


def _accepts_kwargs(fn: Any, required_names: tuple[str, ...]) -> bool:
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    params = sig.parameters.values()
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params):
        return True
    param_names = set(sig.parameters.keys())
    return all(name in param_names for name in required_names)


class _UtteranceRestTimer:
    """Count observed rest time, pausing across brief tracking losses."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._last_timestamp: float | None = None
        self._last_rest: float | None = None
        self._rest_seconds = 0.0

    def observe(self, timestamp: float, arms: list[str | None]) -> bool:
        previous_timestamp = self._last_timestamp
        self._last_timestamp = timestamp
        timestamp_gap = (
            previous_timestamp is not None
            and timestamp - previous_timestamp > self._config.gap + TIMESTAMP_TOLERANCE
        )
        if timestamp_gap or "active" in arms:
            self._last_rest = None
            self._rest_seconds = 0.0

        if not all(arm == "rest" for arm in arms):
            return False

        if self._last_rest is not None:
            elapsed = timestamp - self._last_rest
            if self._last_rest == previous_timestamp:
                self._rest_seconds += elapsed
            elif elapsed > UTTERANCE_TRACKING_GRACE_SECONDS + TIMESTAMP_TOLERANCE:
                self._rest_seconds = 0.0

        self._last_rest = timestamp
        return self._rest_seconds + TIMESTAMP_TOLERANCE >= self._config.utterance_rest


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
        self._classifier_accepts_stream = _accepts_kwargs(
            classifier_fn, ("session_id", "start", "end", "target_seq")
        )
        self.config = config or replace(load_frozen_config(), utterance_rest=DEFAULT_UTTERANCE_REST_SECONDS)
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
        self._utterance_rest = _UtteranceRestTimer(self.config)
        self._utterance_id = 0
        self._utterance_has_segments = False
        self._ring = FrameRingBuffer(max_seconds=ring_seconds)
        # Unbounded queue for tiny control events; heavy segment jobs are capped by _pending_segments.
        self._work_queue: queue.Queue[dict[str, Any]] = queue.Queue()
        self._pending_segments = 0

        self._capture_thread: threading.Thread | None = None
        self._pose_thread: threading.Thread | None = None
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
        self._pose_fps = 0.0
        self._pose_frames: deque[tuple[int, float, np.ndarray]] = deque()
        self._last_streamed_seq = 0
        self._pose_cond = threading.Condition()

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

    def pick_gloss_candidate(
        self, session_id: str, segment_id: str, label_id: int, *, allow_closed: bool = False
    ) -> dict[str, Any]:
        with self._state_lock:
            if session_id != self._session_id:
                raise ValueError("Phiên ký đã thay đổi.")
            for index, record in enumerate(self._glosses):
                if record["segment_id"] == segment_id:
                    break
            else:
                raise ValueError("Không tìm thấy ký hiệu trong phiên này.")

            selected = record.get("selected_candidate")
            if selected is not None:
                if selected["label_id"] == label_id:
                    return record
                raise ValueError("Ký hiệu này đã được xác nhận.")
            if record["utterance_id"] in self._closed_utterances and not allow_closed:
                raise ValueError("Lượt ký đã chốt.")
            if not record["raw"]["low_confidence"]:
                raise ValueError("Ký hiệu này đã rõ.")
            candidate = next(
                (item for item in record["raw"]["top5"][:3] if item["label_id"] == label_id),
                None,
            )
            if candidate is None:
                raise ValueError("Ứng viên nằm ngoài ba gợi ý của ký hiệu.")

            updated = {**record, "selected_candidate": candidate}
            self._glosses[index] = updated
            pending = self._pending_utterance_items.get(record["utterance_id"])
            if pending is not None:
                pending[pending.index(record)] = updated
            self._emit("gloss_corrected", {"gloss": updated})
            return updated

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
                "pose_fps": round(self._pose_fps, 1),
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
            self._utterance_rest = _UtteranceRestTimer(self.config)
            self._utterance_id = 0
            self._utterance_has_segments = False
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
            self._pose_fps = 0.0
            with self._pose_cond:
                self._pose_frames.clear()
            self._last_streamed_seq = 0
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

        if video_path:
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
        else:
            self._capture_thread = threading.Thread(
                target=self._camera_reader_loop,
                args=(session_id, epoch, camera_index),
                daemon=True,
                name="m2-capture-reader",
            )
            self._capture_thread.start()
            self._capture_open_event.wait(timeout=3.0)
            if self._capture_open_error is not None:
                err = self._capture_open_error
                self.stop_session(wait_timeout=1.0)
                with self._state_lock:
                    self._last_error = str(err)
                raise ValueError(str(err))
            self._pose_thread = threading.Thread(
                target=self._pose_consumer_loop,
                args=(session_id, epoch),
                daemon=True,
                name="m2-pose-seg",
            )
            self._pose_thread.start()
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
        segmenter_events = self._segmenter.feed(timestamp, arms)
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
                    "pose_fps": round(self._pose_fps, 1),
                },
            )

        # M1 owns segment boundaries. M2 owns utterance IDs and the pause-aware rest clock.
        events = [
            self._handle_segmenter_event(ev)
            for ev in segmenter_events
            if ev.get("type") != "utterance_end"
        ]
        if self._utterance_rest.observe(timestamp, arms) and self._utterance_has_segments:
            ended = {
                "type": "utterance_end",
                "utterance_id": str(self._utterance_id),
                "timestamp": timestamp,
            }
            self._enqueue_work({"kind": "utterance_end", **ended})
            self._utterance_id += 1
            self._utterance_has_segments = False
            events.append(ended)
        return events

    def _handle_segmenter_event(self, ev: dict[str, Any]) -> dict[str, Any]:
        ev = {**ev, "utterance_id": str(self._utterance_id)}
        status = ev.get("status")
        if status == "complete":
            frames, timestamps = self._ring.slice(ev["start"], ev["end"])
            if not frames:
                incomplete = {**ev, "status": "incomplete", "reason": "empty_buffer_slice"}
                with self._state_lock:
                    self._incomplete_events.append(incomplete)
                self._emit("segment_incomplete", {"segment": incomplete})
                return ev

            self._emit("segment_complete", {"segment": ev, "frame_count": len(frames)})
            queued = self._enqueue_work(
                {
                    "kind": "segment",
                    "session_id": self._session_id,
                    "segment": ev,
                    "frames": frames,
                    "timestamps": timestamps,
                    "target_seq": self._last_streamed_seq,
                    "enqueued_at": time.perf_counter(),
                }
            )
            self._utterance_has_segments |= queued
        elif status == "incomplete":
            with self._state_lock:
                self._incomplete_events.append(ev)
            self._emit("segment_incomplete", {"segment": ev})
        return ev

    def _enqueue_work(self, item: dict[str, Any]) -> bool:
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
                return False
        self._work_queue.put_nowait(item)
        return True

    def stop_session(self, wait_timeout: float = 120.0) -> dict[str, Any]:
        """Stop capturing, mark open movement incomplete, drain already-completed segments, keep history."""
        with self._state_lock:
            if not self._running and not self._draining:
                return self.snapshot()
            self._running = False
            self._draining = True
            self._stop_event.set()
            capture_thread = self._capture_thread
            pose_thread = self._pose_thread
            worker_thread = self._worker_thread

        with self._pose_cond:
            self._pose_frames.clear()
            self._pose_cond.notify_all()

        if capture_thread is not None and capture_thread.is_alive() and capture_thread is not threading.current_thread():
            capture_thread.join(timeout=5.0)
        if pose_thread is not None and pose_thread.is_alive() and pose_thread is not threading.current_thread():
            pose_thread.join(timeout=5.0)

        # Mark any open movement incomplete (end_of_file), keeping already-queued completed segments.
        for ev in self._segmenter.finish():
            self._handle_segmenter_event(ev)

        # Push deterministic end sentinel so FIFO worker drains all queued segments first.
        self._work_queue.put({"kind": "session_end", "timestamp": self._segmenter.last or 0.0})

        if worker_thread is not None and worker_thread.is_alive() and worker_thread is not threading.current_thread():
            worker_thread.join(timeout=wait_timeout)

        with self._state_lock:
            self._draining = False
            self._capture_thread = None
            self._pose_thread = None
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
            accepts_stream = _accepts_kwargs(self._pose_provider, ("ts", "seq", "run_hands"))

            def _remote_pose(
                bgr: np.ndarray,
                *,
                ts: float | None = None,
                seq: int | None = None,
                run_hands: bool = False,
            ) -> tuple[list[list[float]], list[float]]:
                if accepts_stream:
                    return self._pose_provider(
                        bgr,
                        session_id,
                        ts=ts,
                        seq=seq,
                        run_hands=run_hands,
                    )
                return self._pose_provider(bgr, session_id)

            yield _remote_pose
            return
        import mediapipe as mp

        with mp.solutions.pose.Pose(model_complexity=1, smooth_landmarks=False) as pose_model:
            def _local_pose(bgr: np.ndarray, **_kwargs: Any) -> tuple[list[list[float]], list[float]]:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                pose_res = pose_model.process(rgb)
                return extract_pose_8(pose_res)

            yield _local_pose

    def _estimate_arm_states(
        self,
        estimate_pose: Callable[..., tuple[list[list[float]], list[float]]],
        bgr: np.ndarray,
        last_pose_err_emit: float,
        *,
        epoch: int,
        ts: float | None = None,
        seq: int | None = None,
        run_hands: bool = False,
    ) -> tuple[list[str | None] | None, float]:
        pose_error: Exception | None = None
        try:
            pose, visibility = estimate_pose(bgr, ts=ts, seq=seq, run_hands=run_hands)
            arms = arm_states(pose, visibility, self.config)
        except Exception as exc:
            pose_error = exc
            arms = [None, None]

        with self._state_lock:
            # A slow response can arrive after Stop or after the next session starts.
            if not self._running or epoch != self._epoch:
                return None, last_pose_err_emit
            if pose_error is None:
                if seq is not None:
                    self._last_streamed_seq = int(seq)
                if self._last_error and self._last_error.startswith("Không kết nối được Vision Backend"):
                    self._last_error = None
                return arms, last_pose_err_emit
            now_err = time.perf_counter()
            if now_err - last_pose_err_emit < 5.0:
                return arms, last_pose_err_emit
            err_msg = (
                "Không kết nối được Vision Backend trên Laptop "
                f"— hãy mở Firewall cổng 8767 trên Windows ({pose_error})."
            )
            self._last_error = err_msg
        self._emit("error", {"message": err_msg})
        return arms, now_err

    def _camera_reader_loop(
        self,
        session_id: str,
        epoch: int,
        camera_index: int,
    ) -> None:
        cap = None
        try:
            cap = self._open_capture(camera_index, None)
            self._capture_open_event.set()
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            cap.set(cv2.CAP_PROP_FPS, 30)
            buf_prop = getattr(cv2, "CAP_PROP_BUFFERSIZE", None)
            if buf_prop is not None:
                try:
                    cap.set(buf_prop, 1)
                except Exception:
                    pass

            t0 = time.perf_counter()
            last_ts = -1.0
            sequence = 0
            fps_window: deque[float] = deque(maxlen=40)
            target_interval = 0.05  # Cap live ring buffer capture at 20 FPS

            while not self._stop_event.is_set():
                with self._pose_cond:
                    self._pose_cond.wait_for(
                        lambda: self._stop_event.is_set()
                        or epoch != self._epoch
                        or len(self._pose_frames) < MAX_PENDING_POSE_FRAMES
                    )
                    if self._stop_event.is_set() or epoch != self._epoch:
                        break

                loop_start = time.perf_counter()
                ok, bgr = cap.read()
                if self._stop_event.is_set() or epoch != self._epoch:
                    break
                if not ok:
                    time.sleep(0.01)
                    continue

                now = time.perf_counter()
                ts = now - t0
                if ts <= last_ts:
                    ts = last_ts + 1e-4
                last_ts = ts

                self._ring.append(ts, bgr)
                with self._frame_lock:
                    self._latest_frame = bgr.copy()

                fps_window.append(now)
                if len(fps_window) >= 2 and fps_window[-1] > fps_window[0]:
                    self._capture_fps = (len(fps_window) - 1) / (fps_window[-1] - fps_window[0])

                with self._pose_cond:
                    if self._stop_event.is_set() or epoch != self._epoch:
                        break
                    sequence += 1
                    self._pose_frames.append((sequence, ts, bgr))
                    self._pose_cond.notify_all()

                remaining = target_interval - (time.perf_counter() - loop_start)
                if remaining > 0.002:
                    self._stop_event.wait(remaining)
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
            with self._pose_cond:
                self._pose_cond.notify_all()
            if self._running and epoch == self._epoch and self._capture_open_error is None:
                threading.Thread(target=self.stop_session, daemon=True, name="m2-auto-stop").start()

    def _pose_consumer_loop(self, session_id: str, epoch: int) -> None:
        try:
            fps_window: deque[float] = deque(maxlen=30)
            last_pose_err_emit = -10.0

            with self._pose_context(session_id) as estimate_pose:
                while True:
                    with self._pose_cond:
                        self._pose_cond.wait_for(
                            lambda: self._stop_event.is_set()
                            or epoch != self._epoch
                            or bool(self._pose_frames)
                        )
                        if self._stop_event.is_set() or epoch != self._epoch:
                            return
                        sequence, ts, bgr = self._pose_frames.popleft()
                        self._pose_cond.notify_all()

                    with self._state_lock:
                        want_hands = (
                            self._segmenter.state in ("CAPTURING", "END_PENDING")
                            or self._segmenter.onset_since is not None
                        )
                    arms, last_pose_err_emit = self._estimate_arm_states(
                        estimate_pose,
                        bgr,
                        last_pose_err_emit,
                        epoch=epoch,
                        ts=ts,
                        seq=sequence,
                        run_hands=want_hands,
                    )
                    if arms is None:
                        return
                    now = time.perf_counter()
                    fps_window.append(now)
                    if len(fps_window) >= 2 and fps_window[-1] > fps_window[0]:
                        self._pose_fps = (len(fps_window) - 1) / (fps_window[-1] - fps_window[0])

                    self.feed_step(ts, arms, frame=None)
        except Exception as error:
            with self._state_lock:
                if not self._running or epoch != self._epoch:
                    return
                self._last_error = str(error)
            self._emit("error", {"message": str(error)})

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

                    with self._state_lock:
                        want_hands = (
                            self._segmenter.state in ("CAPTURING", "END_PENDING")
                            or self._segmenter.onset_since is not None
                        )
                    arms, last_pose_err_emit = self._estimate_arm_states(
                        estimate_pose,
                        bgr,
                        last_pose_err_emit,
                        epoch=epoch,
                        ts=ts,
                        seq=frame_idx,
                        run_hands=want_hands,
                    )
                    if arms is None:
                        return
                    self._pose_fps = self._capture_fps

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
            if self._running and epoch == self._epoch and self._capture_open_error is None:
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
                    if self._classifier_accepts_stream:
                        pred = self._classifier_fn(
                            item["frames"],
                            item["timestamps"],
                            session_id=item.get("session_id"),
                            start=seg["start"],
                            end=seg["end"],
                            target_seq=item.get("target_seq"),
                        )
                    else:
                        pred = self._classifier_fn(item["frames"], item["timestamps"])
                    end_to_display = time.perf_counter() - item["enqueued_at"]
                    timing_info: dict[str, Any] = {
                        "preprocessing_seconds": pred.get("preprocessing_seconds", 0.0),
                        "inference_seconds": pred.get("inference_seconds", 0.0),
                        "network_seconds": pred.get("network_seconds", 0.0),
                        "queue_and_classify_seconds": end_to_display,
                        "streaming_used": bool(pred.get("streaming_used", False)),
                    }
                    if "catchup_hands_frames" in pred:
                        timing_info["catchup_hands_frames"] = int(pred["catchup_hands_frames"])
                    if "inference_backend" in pred:
                        timing_info["inference_backend"] = pred["inference_backend"]
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
                        "timing": timing_info,
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
