"""Opt-in timing for a single live camera session on the M2 edge."""
from collections import Counter, deque
import math
import threading
import time
from typing import Any


class PoseMetrics:
    def __init__(self, session_id: str, target_fps: int, fifo_capacity: int) -> None:
        self.session_id = session_id
        self.target_fps = target_fps
        self.fifo_capacity = fifo_capacity
        self._lock = threading.Lock()
        self._started = time.perf_counter()
        self._capture_ended: float | None = None
        self._pending: dict[int, float] = {}
        self._samples: deque[dict[str, Any]] = deque(maxlen=15000)
        self._counts: Counter[str] = Counter()
        self._peak_pending = 0

    def capture(self, seq: int, captured_at: float) -> None:
        with self._lock:
            self._counts["captured"] += 1
            self._pending[seq] = captured_at
            self._peak_pending = max(self._peak_pending, len(self._pending))

    def drop(self, seq: int) -> None:
        with self._lock:
            self._pending.pop(seq)
            self._counts["dropped_before_send"] += 1

    def stop_capture(self) -> None:
        with self._lock:
            self._capture_ended = time.perf_counter()

    def discard_pending(self) -> None:
        with self._lock:
            self._counts["discarded_at_stop"] += len(self._pending)
            self._pending.clear()

    def dequeue(self, seq: int) -> dict[str, Any]:
        with self._lock:
            captured_at = self._pending.pop(seq)
            self._counts["dequeued"] += 1
        now = time.perf_counter()
        return {
            "seq": seq,
            "captured_at": captured_at,
            "fifo_ms": (now - captured_at) * 1000,
        }

    def finish(self, sample: dict[str, Any]) -> None:
        with self._lock:
            self._counts["sent"] += int("send_at" in sample)
            self._counts["pose_replies" if sample["ok"] else "pose_errors"] += 1
            self._samples.append(sample)

    def report(self, include_frames: bool) -> dict[str, Any]:
        with self._lock:
            elapsed = (self._capture_ended or time.perf_counter()) - self._started
            counts = dict.fromkeys(
                ("captured", "dequeued", "sent", "pose_replies", "pose_errors",
                 "discarded_at_stop", "dropped_before_send"), 0,
            )
            counts.update(self._counts)
            counts["pending"] = len(self._pending)
            counts["in_flight"] = counts["dequeued"] - counts["pose_replies"] - counts["pose_errors"]
            peak_pending = self._peak_pending
            samples = list(self._samples)
        values: dict[str, list[float]] = {}
        for sample in samples:
            if sample["ok"]:
                for key, value in sample.items():
                    if key.endswith("_ms"):
                        values.setdefault(key, []).append(value)
        summary = {}
        for metric, durations in values.items():
            durations.sort()
            size = len(durations)
            summary[metric] = {
                "n": size,
                "p50": round(durations[math.ceil(size * 0.50) - 1], 3),
                "p95": round(durations[math.ceil(size * 0.95) - 1], 3),
            }
        report = {
            "session_id": self.session_id,
            "target_capture_fps": self.target_fps,
            "capture_seconds": round(elapsed, 3),
            "fifo_capacity": self.fifo_capacity,
            "fifo_peak_pending": peak_pending,
            "counts": counts,
            "retained_frames": len(samples),
            "evicted_frame_samples": counts["pose_replies"] + counts["pose_errors"] - len(samples),
            "successful_frame_timings_ms": summary,
        }
        if include_frames:
            report["frames"] = [
                {
                    key: round((value - self._started) * 1000, 3) if key.endswith("_at") else value
                    for key, value in sample.items()
                }
                for sample in samples
            ]
            report["frame_clock"] = "Fields ending in _at are Pi milliseconds since measurement started"
        return report
