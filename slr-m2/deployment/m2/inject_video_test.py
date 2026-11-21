"""Inject local test videos into a running M2.1 server and capture timestamped WebSocket traces."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import time
from typing import Any

import cv2
import httpx
import numpy as np
import websockets

from deployment.m1.common import ROOT
from deployment.m1.segmenter import arm_states
from deployment.m2.pipeline import _extract_pose_8, load_frozen_config

LOCAL_DATA_DIR = ROOT.parent / "slr-app" / "MVP" / "local_data"
DEFAULT_DEMO_CLIPS = [
    LOCAL_DATA_DIR / "014159.mp4",
    LOCAL_DATA_DIR / "007272.mp4",
]
DEFAULT_OUT_TRACE = ROOT / "outputs" / "e2e_inject_trace.json"
DEFAULT_SEQ_VIDEO = ROOT / "outputs" / "demo_sequence_vsl400.mp4"


def _find_rest_frame(clip_path: Path, pose_model: Any, cfg: Any) -> np.ndarray:
    """Return a frame from clip_path where both arms satisfy M1's rest posture if available."""
    cap = cv2.VideoCapture(str(clip_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open clip: {clip_path}")
    frames: list[np.ndarray] = []
    try:
        while True:
            ok, bgr = cap.read()
            if not ok:
                break
            frames.append(bgr)
    finally:
        cap.release()

    if not frames:
        raise ValueError(f"Clip has no frames: {clip_path}")

    # Check boundary frames first (start & tail are most likely to be neutral rest).
    candidate_indices = list(range(min(8, len(frames)))) + list(
        range(max(0, len(frames) - 10), len(frames))
    )
    seen: set[int] = set()
    for idx in candidate_indices:
        if idx in seen:
            continue
        seen.add(idx)
        rgb = cv2.cvtColor(frames[idx], cv2.COLOR_BGR2RGB)
        pose_res = pose_model.process(rgb)
        pose, vis = _extract_pose_8(pose_res)
        arms = arm_states(pose, vis, cfg)
        if arms == ["rest", "rest"]:
            return frames[idx]

    # Fallback: scan full clip before giving up.
    for idx, frame in enumerate(frames):
        if idx in seen:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose_res = pose_model.process(rgb)
        pose, vis = _extract_pose_8(pose_res)
        arms = arm_states(pose, vis, cfg)
        if arms == ["rest", "rest"]:
            return frame

    return frames[0]


def build_demo_sequence(
    clip_paths: list[Path],
    output_video: Path,
    fps: float = 25.0,
    lead_rest_s: float = 1.0,
    mid_rest_s: float = 0.20,
    tail_rest_s: float = 2.2,
) -> Path:
    """Concatenate VSL400 clips with verified arms-down rest padding to trigger 0.35s / 1.5s timers."""
    import mediapipe as mp

    existing = [Path(p).resolve() for p in clip_paths if Path(p).is_file()]
    if not existing:
        raise FileNotFoundError("No VSL400 sample clips found to build demo sequence")

    cfg = load_frozen_config()
    cap0 = cv2.VideoCapture(str(existing[0]))
    width = int(cap0.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap0.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap0.release()
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid video dimensions in {existing[0]}")

    output_video = Path(output_video).resolve()
    output_video.parent.mkdir(parents=True, exist_ok=True)

    with mp.solutions.pose.Pose(model_complexity=1, smooth_landmarks=False) as pose_model:
        rest_frames = [_find_rest_frame(p, pose_model, cfg) for p in existing]

    writer = cv2.VideoWriter(
        str(output_video),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Cannot open VideoWriter for {output_video}")

    def _fit(frame: np.ndarray) -> np.ndarray:
        if frame.shape[1] == width and frame.shape[0] == height:
            return frame
        return cv2.resize(frame, (width, height))

    def _write_rest(frame: np.ndarray, seconds: float) -> None:
        fitted = _fit(frame)
        count = max(1, int(round(seconds * fps)))
        for _ in range(count):
            writer.write(fitted)

    try:
        _write_rest(rest_frames[0], lead_rest_s)
        for idx, clip in enumerate(existing):
            cap = cv2.VideoCapture(str(clip))
            try:
                while True:
                    ok, frame = cap.read()
                    if not ok:
                        break
                    writer.write(_fit(frame))
            finally:
                cap.release()
            hold = tail_rest_s if idx == len(existing) - 1 else mid_rest_s
            _write_rest(rest_frames[idx], hold)
    finally:
        writer.release()

    return output_video


async def run_injection(
    base_url: str,
    video_path: Path,
    realtime: bool,
    timeout_seconds: float,
) -> dict[str, Any]:
    base = base_url.rstrip("/")
    ws_url = base.replace("https://", "wss://", 1).replace("http://", "ws://", 1) + "/ws/live"

    trace: dict[str, Any] = {
        "base_url": base,
        "video_path": str(video_path),
        "realtime_video": realtime,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "health": None,
        "tts_probe": None,
        "stopped_prior_session": False,
        "events": [],
        "final_snapshot": None,
        "error": None,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        health_res = await client.get(f"{base}/api/health")
        health_res.raise_for_status()
        trace["health"] = health_res.json()

        tts_res = await client.get(f"{base}/api/tts/95.mp3")
        trace["tts_probe"] = {
            "status_code": tts_res.status_code,
            "content_type": tts_res.headers.get("content-type"),
            "bytes": len(tts_res.content) if tts_res.status_code == 200 else 0,
        }

        if trace["health"].get("running") or trace["health"].get("draining"):
            await client.post(f"{base}/api/session/stop")
            trace["stopped_prior_session"] = True
            await asyncio.sleep(0.3)

        t0 = time.perf_counter()
        async with websockets.connect(ws_url, open_timeout=10.0) as ws:
            # Consume initial snapshot before starting injected video session.
            try:
                raw_init = await asyncio.wait_for(ws.recv(), timeout=5.0)
                init_msg = json.loads(raw_init)
                trace["events"].append({"elapsed_s": 0.0, **init_msg})
            except asyncio.TimeoutError:
                pass

            start_res = await client.post(
                f"{base}/api/session/start",
                json={
                    "video_path": str(video_path),
                    "realtime_video": realtime,
                },
            )
            if start_res.status_code >= 400:
                raise RuntimeError(
                    f"POST /api/session/start failed ({start_res.status_code}): {start_res.text}"
                )

            deadline = t0 + timeout_seconds
            while time.perf_counter() < deadline:
                remaining = max(0.5, deadline - time.perf_counter())
                try:
                    raw_msg = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 2.0))
                except asyncio.TimeoutError:
                    continue

                msg = json.loads(raw_msg)
                elapsed = round(time.perf_counter() - t0, 3)
                event_entry = {"elapsed_s": elapsed, **msg}
                trace["events"].append(event_entry)

                etype = msg.get("type")
                if etype == "status":
                    print(
                        f"[{elapsed:6.2f}s] STATUS -> {msg.get('segmenter_state')} "
                        f"arms={msg.get('arms')} fps={msg.get('capture_fps')} q={msg.get('queue_depth')}",
                        flush=True,
                    )
                elif etype == "segment_complete":
                    seg = msg.get("segment", {})
                    print(
                        f"[{elapsed:6.2f}s] SEGMENT #{seg.get('segment_id')} COMPLETE "
                        f"({msg.get('frame_count')} frames)",
                        flush=True,
                    )
                elif etype == "segment_incomplete":
                    seg = msg.get("segment", {})
                    print(
                        f"[{elapsed:6.2f}s] SEGMENT #{seg.get('segment_id')} INCOMPLETE "
                        f"({seg.get('reason')})",
                        flush=True,
                    )
                elif etype == "gloss_result":
                    g = msg.get("gloss", {})
                    raw = g.get("raw", {})
                    timing = g.get("timing", {})
                    print(
                        f"[{elapsed:6.2f}s] GLOSS #{g.get('segment_id')}: "
                        f"{raw.get('top1_label')} ({raw.get('confidence', 0)*100:.1f}%) "
                        f"low={raw.get('low_confidence')} "
                        f"[pre={timing.get('preprocessing_seconds', 0):.2f}s, "
                        f"gcn={timing.get('inference_seconds', 0):.3f}s]",
                        flush=True,
                    )
                elif etype == "utterance_ready":
                    u = msg.get("utterance", {})
                    print(
                        f"[{elapsed:6.2f}s] UTTERANCE #{u.get('utterance_id')} ({u.get('reason')}): "
                        f"{u.get('raw_glosses')}",
                        flush=True,
                    )
                elif etype == "error":
                    print(f"[{elapsed:6.2f}s] ERROR: {msg.get('message')}", flush=True)
                elif etype == "session_stopped":
                    trace["final_snapshot"] = msg.get("snapshot")
                    print(f"[{elapsed:6.2f}s] SESSION STOPPED cleanly.", flush=True)
                    break

        if trace["final_snapshot"] is None:
            state_res = await client.get(f"{base}/api/state")
            if state_res.status_code == 200:
                trace["final_snapshot"] = state_res.json()

    return trace


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject local test video into M2.1 server")
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--video", type=Path, help="Direct path to local .mp4/.avi test video")
    parser.add_argument(
        "--demo-sequence",
        action="store_true",
        help="Build a multi-sign sequence with rest padding from local VSL400 clips",
    )
    parser.add_argument("--realtime", dest="realtime", action="store_true", default=True)
    parser.add_argument("--no-realtime", dest="realtime", action="store_false")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_TRACE)
    args = parser.parse_args()

    if args.video:
        target_video = Path(args.video).resolve()
        if not target_video.is_file():
            raise SystemExit(f"Video not found: {target_video}")
    else:
        target_video = build_demo_sequence(DEFAULT_DEMO_CLIPS, DEFAULT_SEQ_VIDEO)
        print(f"Built demo sequence video: {target_video}", flush=True)

    trace = asyncio.run(
        run_injection(
            base_url=args.base_url,
            video_path=target_video,
            realtime=args.realtime,
            timeout_seconds=args.timeout,
        )
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved trace JSON: {args.out.resolve()}", flush=True)


if __name__ == "__main__":
    main()
