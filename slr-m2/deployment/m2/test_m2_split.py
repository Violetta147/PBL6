"""Verification suite for M2.2 Vision/Bone split serialization, endpoints, fallback, and 07b parity."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest import mock

import cv2
from fastapi.testclient import TestClient
import numpy as np

from deployment.m1.common import DEFAULT_BUNDLE, ROOT
from deployment.m2.classifier import (
    BONE_WIRE_KEYS,
    BoneClassifier,
    VisionExtractor,
    decode_bundle_bytes_to_frames,
    deserialize_landmark_arrays,
    encode_frames_to_bundle_bytes,
    encode_frames_to_clip_bytes,
    serialize_landmark_arrays,
)
from deployment.m2.pipeline import LiveSessionManager
from deployment.m2.remote_clients import RemotePoseClient, SplitClassifierClient
from deployment.m2.server import create_app
from deployment.m2.vision_backend import create_vision_app

SAMPLE_CLIP = Path(r"C:\Users\LAPTOP T&T\VIOLETTA\Documents\ChatGPT\PBL6\slr-app\MVP\local_data\014159.mp4")


def _synthetic_arrays(frames: int = 24) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(7)
    xy = rng.normal(0.0, 0.2, size=(frames, 50, 2)).astype(np.float32)
    xy[:, 0, :] = np.array([-0.5, 0.0], dtype=np.float32)
    xy[:, 1, :] = np.array([0.5, 0.0], dtype=np.float32)
    return {
        "xy": xy,
        "usable_mask": np.ones((frames, 50), dtype=bool),
        "observed_mask": np.ones((frames, 50), dtype=bool),
        "imputed_mask": np.zeros((frames, 50), dtype=bool),
        "timestamps": np.linspace(0.0, 0.92, num=frames, dtype=np.float64),
        "frame_indices": np.arange(frames, dtype=np.int64),
        "association_method": np.full((frames, 2), "pose", dtype="<U8"),
        "normalization_fallback": np.zeros(frames, dtype=bool),
    }


def _dummy_bgr_frames(count: int = 6) -> tuple[list[np.ndarray], list[float]]:
    frames = [np.full((64, 64, 3), (i * 25) % 255, dtype=np.uint8) for i in range(count)]
    timestamps = [i * 0.04 for i in range(count)]
    return frames, timestamps


def _fake_vision_extractor():
    class _FakeVision:
        def __init__(self) -> None:
            self.calls = 0

        def extract_landmarks(self, _video_path: Path):
            self.calls += 1
            return _synthetic_arrays(), {"frames": 24, "normalized_usable_fraction": 1.0}, False, 0.02

        def extract_from_frames(self, _frames, _timestamps, **_kwargs):
            self.calls += 1
            return _synthetic_arrays(), {"frames": 24, "normalized_usable_fraction": 1.0}, False, 0.02

    return _FakeVision()


def _fake_bone_classifier(inference_seconds: float = 0.02):
    class _FakeBone:
        def __init__(self) -> None:
            self.identity = {"bundle": "fake-07b", "checkpoint_sha256": "abc"}
            self.calls = 0
            self.infer_delay = float(inference_seconds)

        def infer_from_arrays(self, arrays: dict[str, np.ndarray], inference_executor: str = "local"):
            self.calls += 1
            return {
                "top1_label": "Dài",
                "top1_id": 95,
                "confidence": 0.99,
                "low_confidence": False,
                "top5": [{"label": "Dài", "label_id": 95, "score": 0.99}],
                "inference_seconds": self.infer_delay,
                "inference_executor": inference_executor,
                "source_frames": int(len(arrays["xy"])),
                "repeated_positions": max(0, 150 - int(len(arrays["xy"]))),
                "truncated_frames": 0,
            }

    return _FakeBone()


class M2SplitWireTests(unittest.TestCase):
    def test_landmark_npz_roundtrip_without_pickle(self):
        orig = _synthetic_arrays(frames=40)
        payload = serialize_landmark_arrays(orig)
        self.assertGreater(len(payload), 0)
        self.assertLess(len(payload), 100_000)

        decoded = deserialize_landmark_arrays(payload)
        self.assertEqual(set(decoded.keys()), set(BONE_WIRE_KEYS))
        np.testing.assert_allclose(decoded["xy"], orig["xy"])
        np.testing.assert_array_equal(decoded["usable_mask"], orig["usable_mask"])
        np.testing.assert_array_equal(decoded["association_method"], orig["association_method"])

    def test_frame_bundle_roundtrip_preserves_shapes_and_timestamps(self):
        frames, timestamps = _dummy_bgr_frames(count=8)
        payload = encode_frames_to_bundle_bytes(frames, timestamps, jpeg_quality=90)
        self.assertGreater(len(payload), 0)
        decoded_frames, decoded_ts = decode_bundle_bytes_to_frames(payload)
        self.assertEqual(len(decoded_frames), len(frames))
        self.assertEqual([f.shape for f in decoded_frames], [f.shape for f in frames])
        np.testing.assert_allclose(decoded_ts, timestamps)

    def test_bone_classifier_imports_zero_mediapipe_in_isolated_process(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT)
        code = (
            "import sys; "
            "from deployment.m2.classifier import BoneClassifier; "
            "clf = BoneClassifier(); "
            "assert 'mediapipe' not in sys.modules, 'mediapipe should not load on Pi Edge'; "
            "assert clf.identity['checkpoint_sha256']"
        )
        res = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, msg=res.stderr)


class M2SplitContractAndFallbackTests(unittest.TestCase):
    def test_vision_backend_contract_and_size_bounds(self):
        fake_pose = lambda _bgr, _sid: ([[0.5, 0.5, 0.0]] * 8, [0.95] * 8)
        vision_ext = _fake_vision_extractor()
        fallback_bone = _fake_bone_classifier(inference_seconds=0.01)
        app = create_vision_app(
            enable_fallback_classifier=True,
            vision_extractor=vision_ext,
            bone_classifier=fallback_bone,
            pose_detector=fake_pose,
        )

        with TestClient(app) as client:
            health = client.get("/api/vision/health")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json()["role"], "vision_backend")
            self.assertTrue(health.json()["fallback_classifier_loaded"])

            reset_res = client.post("/api/vision/pose-reset?session_id=s1")
            self.assertEqual(reset_res.status_code, 200)
            self.assertTrue(reset_res.json()["ok"])

            img = np.zeros((48, 64, 3), dtype=np.uint8)
            ok, jpg = cv2.imencode(".jpg", img)
            self.assertTrue(ok)
            pose_res = client.post(
                "/api/vision/pose-frame?session_id=s1",
                content=jpg.tobytes(),
                headers={"Content-Type": "image/jpeg"},
            )
            self.assertEqual(pose_res.status_code, 200)
            self.assertEqual(len(pose_res.json()["pose"]), 8)
            self.assertEqual(len(pose_res.json()["visibility"]), 8)

            self.assertEqual(client.post("/api/vision/pose-frame", content=b"").status_code, 400)
            self.assertEqual(client.post("/api/vision/pose-frame", content=b"not-jpeg").status_code, 400)

            frames, ts = _dummy_bgr_frames()
            clip_bytes, ext = encode_frames_to_clip_bytes(frames, ts, prefer_compact=True)
            self.assertEqual(ext, ".avi")

            bad_ext = client.post("/api/vision/extract-landmarks?ext=.mov", content=clip_bytes)
            self.assertEqual(bad_ext.status_code, 400)

            too_big = client.post(
                "/api/vision/pose-frame",
                content=b"x",
                headers={"Content-Length": str(10 * 1024 * 1024)},
            )
            self.assertEqual(too_big.status_code, 413)

            ext_res = client.post("/api/vision/extract-landmarks?ext=.avi", content=clip_bytes)
            self.assertEqual(ext_res.status_code, 200)
            arrays = deserialize_landmark_arrays(ext_res.content)
            self.assertEqual(len(arrays["xy"]), 24)

            cls_res = client.post("/api/vision/classify-clip?ext=.avi", content=clip_bytes)
            self.assertEqual(cls_res.status_code, 200)
            self.assertEqual(cls_res.json()["top1_label"], "Dài")
            self.assertEqual(cls_res.json()["inference_executor"], "backend_fallback")

    def test_vision_backend_returns_503_when_fallback_disabled(self):
        app = create_vision_app(
            enable_fallback_classifier=False,
            vision_extractor=_fake_vision_extractor(),
            bone_classifier=None,
            pose_detector=lambda _bgr, _sid: ([[0.0, 0.0, 0.0]] * 8, [0.9] * 8),
        )
        with TestClient(app) as client:
            frames, ts = _dummy_bgr_frames()
            clip_bytes, _ = encode_frames_to_clip_bytes(frames, ts)
            res = client.post("/api/vision/classify-clip?ext=.avi", content=clip_bytes)
            self.assertEqual(res.status_code, 503)

    def test_auto_slow_fallback_and_manual_runtime_toggle(self):
        vision_app = create_vision_app(
            enable_fallback_classifier=True,
            vision_extractor=_fake_vision_extractor(),
            bone_classifier=_fake_bone_classifier(inference_seconds=0.01),
            pose_detector=lambda _bgr, _sid: ([[0.4, 0.5, 0.0]] * 8, [0.99] * 8),
        )
        pi_bone = _fake_bone_classifier(inference_seconds=0.05)

        with TestClient(vision_app) as vision_client:
            split_client = SplitClassifierClient(
                vision_backend_url="http://testserver",
                bone_classifier=pi_bone,
                mode="pi-split",
                fallback_threshold_seconds=1.5,
                consecutive_slow_limit=2,
                http_client=vision_client,
            )
            frames, ts = _dummy_bgr_frames()

            # Fast inference stays pi_local
            r1 = split_client.classify_frames(frames, ts)
            self.assertEqual(r1["inference_executor"], "pi_local")
            self.assertFalse(r1["fallback_triggered"])
            self.assertFalse(split_client.status()["fallback_active"])

            # Slow #1 (< consecutive_slow_limit=2) keeps pi_local
            pi_bone.infer_delay = 1.75
            r2 = split_client.classify_frames(frames, ts)
            self.assertEqual(r2["inference_executor"], "pi_local")
            self.assertFalse(r2["fallback_triggered"])
            self.assertEqual(split_client.status()["consecutive_slow"], 1)

            # Slow #2 trips threshold -> subsequent call goes to backend_fallback
            r3 = split_client.classify_frames(frames, ts)
            self.assertTrue(r3["fallback_triggered"])
            self.assertTrue(split_client.status()["fallback_active"])
            self.assertEqual(split_client.status()["active_executor"], "backend_fallback")

            r4 = split_client.classify_frames(frames, ts)
            self.assertEqual(r4["inference_executor"], "backend_fallback")

            # Also verify Pi edge server /api/health runtime & /api/runtime/fallback toggle
            edge_app = create_app(
                classifier_fn=split_client.classify_frames,
                preload_model=False,
                inference_mode="pi-split",
                vision_backend_url="http://testserver",
                runtime_controller=split_client,
            )
            with TestClient(edge_app) as edge_client:
                h = edge_client.get("/api/health").json()
                self.assertEqual(h["runtime"]["active_executor"], "backend_fallback")

                toggle_off = edge_client.post(
                    "/api/runtime/fallback",
                    json={"fallback_active": False},
                )
                self.assertEqual(toggle_off.status_code, 200)
                self.assertEqual(toggle_off.json()["runtime"]["active_executor"], "pi_local")

                # Verify RemotePoseClient works against vision_backend
                pose_client = RemotePoseClient("http://testserver", http_client=vision_client)
                pose_client.reset("s-pose")
                p8, v8 = pose_client.detect_pose_8(frames[0], "s-pose")
                self.assertEqual(len(p8), 8)
                self.assertEqual(len(v8), 8)


class M2RealSplitParityTests(unittest.TestCase):
    @unittest.skipUnless(SAMPLE_CLIP.is_file(), "Sample VSL400 clip 014159.mp4 not present")
    def test_real_014159_vision_extract_wire_to_pi_bone(self):
        vision = VisionExtractor()
        bone = BoneClassifier(bundle=DEFAULT_BUNDLE)

        arrays, qc, crop_rescue, pre_s = vision.extract_landmarks(SAMPLE_CLIP)
        payload = serialize_landmark_arrays(arrays)
        self.assertLess(len(payload), 100_000)

        decoded = deserialize_landmark_arrays(payload)
        pred = bone.infer_from_arrays(decoded, inference_executor="pi_local")
        self.assertEqual(pred["top1_label"], "Dài")
        self.assertEqual(pred["top1_id"], 95)
        self.assertGreater(pred["confidence"], 0.98)
        self.assertEqual(pred["inference_executor"], "pi_local")

        # Also test compact MJPG LAN transport end-to-end against real Vision Backend
        cap = cv2.VideoCapture(str(SAMPLE_CLIP))
        frames: list[np.ndarray] = []
        timestamps: list[float] = []
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            i = 0
            while True:
                ok, bgr = cap.read()
                if not ok:
                    break
                frames.append(bgr)
                timestamps.append(i / fps)
                i += 1
        finally:
            cap.release()

        vision_app = create_vision_app(
            enable_fallback_classifier=False,
            vision_extractor=vision,
            pose_detector=lambda _bgr, _sid: ([[0.5, 0.5, 0.0]] * 8, [0.9] * 8),
        )
        with TestClient(vision_app) as vision_client:
            split = SplitClassifierClient(
                vision_backend_url="http://testserver",
                bone_classifier=bone,
                mode="pi-split",
                http_client=vision_client,
            )
            res = split.classify_frames(frames, timestamps, fallback_fps=25.0)
            self.assertEqual(res["top1_label"], "Dài")
            self.assertEqual(res["top1_id"], 95)
            self.assertGreater(res["confidence"], 0.95)
            self.assertLess(res["landmark_payload_bytes"], 100_000)
            self.assertEqual(res["inference_executor"], "pi_local")
            print(
                f"\n[M2.2 Split Parity 014159.mp4] top1={res['top1_label']} ({res['confidence']:.4f}) "
                f"wire_npz={res['landmark_payload_bytes']}B net={res['network_seconds']:.3f}s "
                f"pre={pre_s:.2f}s gcn={res['inference_seconds']:.3f}s crop={crop_rescue}"
            )

    @unittest.skipUnless(SAMPLE_CLIP.is_file(), "Sample VSL400 clip 014159.mp4 not present")
    def test_real_014159_pbl6_ram_bundle_warm_parallel_parity(self):
        cap = cv2.VideoCapture(str(SAMPLE_CLIP))
        frames: list[np.ndarray] = []
        timestamps: list[float] = []
        try:
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            i = 0
            while True:
                ok, bgr = cap.read()
                if not ok:
                    break
                frames.append(bgr)
                timestamps.append(i / fps)
                i += 1
        finally:
            cap.release()

        bundle_bytes = encode_frames_to_bundle_bytes(frames, timestamps)
        bone = BoneClassifier(bundle=DEFAULT_BUNDLE)
        vision = VisionExtractor()
        vision_app = create_vision_app(
            enable_fallback_classifier=True,
            vision_extractor=vision,
            bone_classifier=bone,
            pose_detector=lambda _bgr, _sid: ([[0.5, 0.5, 0.0]] * 8, [0.9] * 8),
        )
        with TestClient(vision_app) as client:
            ext_res = client.post("/api/vision/extract-landmarks?ext=.pbl6", content=bundle_bytes)
            self.assertEqual(ext_res.status_code, 200)
            arrays = deserialize_landmark_arrays(ext_res.content)
            pred_pi = bone.infer_from_arrays(arrays, inference_executor="pi_local")
            self.assertEqual(pred_pi["top1_label"], "Dài")
            self.assertGreaterEqual(pred_pi["confidence"], 0.90)

            cls_res = client.post("/api/vision/classify-clip?ext=.pbl6", content=bundle_bytes)
            self.assertEqual(cls_res.status_code, 200)
            body = cls_res.json()
            self.assertEqual(body["top1_label"], "Dài")
            self.assertGreaterEqual(body["confidence"], 0.90)


class LinuxCameraProbeTests(unittest.TestCase):
    def test_linux_open_capture_falls_back_to_working_v4l2_index(self):
        service = LiveSessionManager(classifier_fn=lambda *_a, **_k: {})
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        calls: list[tuple[int, int | None]] = []

        class _FakeCap:
            def __init__(self, idx: int, api: int | None):
                self.idx = idx
                self.api = api
                self.released = False

            def isOpened(self) -> bool:
                return self.idx == 1 and self.api == getattr(cv2, "CAP_V4L2", None)

            def set(self, *_args) -> bool:
                return True

            def get(self, *_args) -> float:
                return 30.0

            def read(self):
                if self.isOpened():
                    return True, dummy_frame
                return False, None

            def release(self) -> None:
                self.released = True

        def fake_video_capture(idx: int, api: int | None = None):
            calls.append((idx, api))
            return _FakeCap(idx, api)

        with (
            mock.patch("deployment.m2.pipeline.platform.system", return_value="Linux"),
            mock.patch.object(service, "_discover_linux_video_nodes", return_value=([0, 1], ["/dev/video0", "/dev/video1"])),
            mock.patch("deployment.m2.pipeline.cv2.VideoCapture", side_effect=fake_video_capture),
        ):
            cap = service._open_capture(0, None)
            self.assertEqual(cap.idx, 1)
            self.assertFalse(cap.released)
            self.assertGreaterEqual(len(calls), 3)

        with (
            mock.patch("deployment.m2.pipeline.platform.system", return_value="Linux"),
            mock.patch.object(service, "_discover_linux_video_nodes", return_value=([], [])),
            mock.patch("deployment.m2.pipeline.cv2.VideoCapture", side_effect=lambda idx, api=None: _FakeCap(99, api)),
        ):
            with self.assertRaisesRegex(ValueError, "/dev/video0..9"):
                service._open_capture(0, None)

            with self.assertRaisesRegex(ValueError, "/dev/video0..9"):
                service.start_camera_session(camera_index=0)
            snap = service.snapshot()
            self.assertFalse(snap["running"])
            self.assertIn("/dev/video0..9", snap["last_error"])

    def test_camera_preview_stays_alive_when_remote_pose_times_out(self):
        def failing_pose(_bgr, _sid):
            raise TimeoutError("timed out")

        service = LiveSessionManager(
            classifier_fn=lambda *_a, **_k: {},
            pose_provider=failing_pose,
            on_capture_start=lambda _sid: (_ for _ in ()).throw(TimeoutError("reset timed out")),
        )
        dummy_frame = np.full((240, 320, 3), 42, dtype=np.uint8)

        class _LiveFakeCap:
            def isOpened(self) -> bool:
                return True

            def set(self, *_args) -> bool:
                return True

            def get(self, *_args) -> float:
                return 30.0

            def read(self):
                time.sleep(0.01)
                return True, dummy_frame

            def release(self) -> None:
                pass

        with mock.patch.object(service, "_open_capture", return_value=_LiveFakeCap()):
            service.start_camera_session(camera_index=0)
            time.sleep(0.15)
            snap = service.snapshot()
            latest = service.get_latest_frame()
            service.stop_session(wait_timeout=2.0)

        self.assertTrue(snap["running"])
        self.assertIsNotNone(latest)
        self.assertEqual(latest.shape, (240, 320, 3))
        self.assertIn("Vision Backend", snap["last_error"] or "")

    def test_extract_pose_8_none_is_strictly_json_compliant_and_arms_unknown(self):
        from deployment.m1.segmenter import arm_states
        from deployment.m2.pipeline import _extract_pose_8, load_frozen_config

        pose, visibility = _extract_pose_8(None)
        encoded = json.dumps({"pose": pose, "visibility": visibility}, allow_nan=False)
        self.assertIn("pose", encoded)
        self.assertEqual(arm_states(pose, visibility, load_frozen_config()), [None, None])

    def test_decoupled_capture_records_denser_ring_frames_than_slow_pose(self):
        pose_calls = 0

        def slow_pose(_bgr, _sid):
            nonlocal pose_calls
            pose_calls += 1
            time.sleep(0.14)
            return [[0.5, 0.5, 0.0]] * 8, [0.95] * 8

        service = LiveSessionManager(
            classifier_fn=lambda *_a, **_k: {},
            pose_provider=slow_pose,
        )
        dummy_frame = np.full((120, 160, 3), 24, dtype=np.uint8)

        class _FastFakeCap:
            def isOpened(self) -> bool:
                return True

            def set(self, *_args) -> bool:
                return True

            def get(self, *_args) -> float:
                return 30.0

            def read(self):
                time.sleep(0.01)
                return True, dummy_frame

            def release(self) -> None:
                pass

        with mock.patch.object(service, "_open_capture", return_value=_FastFakeCap()):
            service.start_camera_session(camera_index=0)
            time.sleep(0.55)
            ring_frames, _ = service._ring.slice(0.0, 10.0)
            snap = service.stop_session(wait_timeout=3.0)

        self.assertFalse(snap["running"])
        self.assertGreater(len(ring_frames), pose_calls + 2)
        self.assertGreaterEqual(pose_calls, 2)


if __name__ == "__main__":
    unittest.main()
