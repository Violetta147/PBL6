"""Verification suite for M2.2 Vision/Bone split serialization, endpoints, fallback, and 07b parity."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock

import cv2
from fastapi.testclient import TestClient
import httpx
import numpy as np

from deployment.m1.common import DEFAULT_BUNDLE, ROOT
from deployment.m2.classifier import (
    BONE_WIRE_KEYS,
    BoneClassifier,
    StreamFrameEntry,
    VisionExtractor,
    decode_bundle_bytes_to_frames,
    deserialize_landmark_arrays,
    encode_frames_to_bundle_bytes,
    encode_frames_to_clip_bytes,
    serialize_landmark_arrays,
)
from deployment.m2.pipeline import LiveSessionManager
from deployment.m2.pose_wire import POSE_FRAME_HEADER, POSE_MEASURE
from deployment.m2.remote_clients import RemotePoseClient, SplitClassifierClient
from deployment.m2.server import create_app
from deployment.m2.vision_backend import create_vision_app

SAMPLE_CLIP = Path(os.environ.get("PBL6_M2_SAMPLE_CLIP", ROOT.parent / "slr-app/MVP/local_data/014159.mp4"))
SAMPLE_NPZ = ROOT / "outputs" / "sample_014159_landmarks.npz"


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
    def test_crop_rescue_is_opt_in_for_all_extraction_paths(self):
        frames, timestamps = _dummy_bgr_frames()
        entries = [
            StreamFrameEntry(seq, ts, frame, pose_res=None, packed={"landmarks": []})
            for seq, (ts, frame) in enumerate(zip(timestamps, frames), start=1)
        ]
        for enabled in (False, True):
            with self.subTest(enabled=enabled):
                extractor = VisionExtractor(crop_rescue_enabled=True) if enabled else VisionExtractor()
                try:
                    full = _synthetic_arrays(len(frames))
                    meta = {"fps": 25.0, "width": 64, "height": 64, "decoded_frames": len(frames)}
                    crop = mock.sentinel.crop
                    extractor._extract_raw = mock.Mock()
                    extractor._extract_raw.assemble_frames.side_effect = lambda *_: dict(full)
                    extractor._extract_raw.extract_video.return_value = (full, meta)
                    extractor._rescue_candidates = mock.Mock()
                    extractor._rescue_candidates.detector_profile.return_value = {}
                    extractor._rescue_candidates.selected.return_value = True
                    extractor._rescue_candidates.extract_crop.return_value = (crop, {})
                    extractor._pilot_extraction = mock.Mock()
                    extractor._pilot = mock.Mock()
                    extractor._pilot.process.return_value = (full, {})
                    with (
                        mock.patch.object(extractor, "_ensure_models_unlocked", return_value=(mock.Mock(), mock.Mock())),
                        mock.patch.object(extractor, "_run_crop_rescue_unlocked", return_value=crop) as run_crop,
                    ):
                        outcomes = (
                            extractor.extract_from_stream_entries(entries),
                            extractor.extract_from_frames(frames, timestamps),
                            extractor.extract_landmarks(Path("sample.mp4")),
                        )
                    self.assertEqual([result[2] for result in outcomes], [enabled] * 3)
                    self.assertEqual(extractor._rescue_candidates.detector_profile.call_count, 3 if enabled else 0)
                    self.assertEqual(extractor._rescue_candidates.selected.call_count, 3 if enabled else 0)
                    self.assertEqual(run_crop.call_count, 2 if enabled else 0)
                    self.assertEqual(extractor._rescue_candidates.extract_crop.call_count, int(enabled))
                    self.assertEqual(
                        [call.args[1] for call in extractor._pilot.process.call_args_list],
                        [crop if enabled else None] * 3,
                    )
                finally:
                    extractor.close()

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
    def test_binary_pose_socket_returns_ordered_replies_and_populates_stream_buffer(self):
        extractor = _fake_vision_extractor()
        def detect_pose(_frame, _session):
            return [[0.0, 0.0, 0.0]] * 8, [0.0] * 8

        app = create_vision_app(
            enable_fallback_classifier=False, vision_extractor=extractor, pose_detector=detect_pose,
        )
        jpeg = cv2.imencode(".jpg", _dummy_bgr_frames()[0][0])[1].tobytes()
        with TestClient(app) as client:
            with client.websocket_connect("/ws/vision/pose?session_id=socket-test") as socket:
                for seq, timestamp in ((1, 0.10), (3, 0.15)):
                    socket.send_bytes(POSE_FRAME_HEADER.pack(seq, timestamp, POSE_MEASURE) + jpeg)
                    result = socket.receive_json()
                    self.assertEqual(result["seq"], seq)
                    self.assertEqual(len(result["pose"]), 8)
                    self.assertIn("decode", result["timing_ms"])
            extracted = client.post("/api/vision/extract-segment", json={
                "session_id": "socket-test", "start": 0.10, "end": 0.15, "target_seq": 3,
            })
        self.assertEqual(extracted.status_code, 200)
        self.assertEqual(extractor.calls, 1)

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

    def test_streaming_segment_endpoints_and_404_fallback_to_pbl6(self):
        vision_app = create_vision_app(
            enable_fallback_classifier=True,
            vision_extractor=_fake_vision_extractor(),
            bone_classifier=_fake_bone_classifier(inference_seconds=0.01),
            pose_detector=lambda _bgr, _sid: ([[0.4, 0.5, 0.0]] * 8, [0.99] * 8),
        )
        pi_bone = _fake_bone_classifier(inference_seconds=0.02)
        frames, ts = _dummy_bgr_frames(count=6)

        with TestClient(vision_app) as vision_client:
            pose_client = RemotePoseClient("http://testserver", http_client=vision_client)
            pose_client.reset("s-stream")
            for idx, (frame, t_val) in enumerate(zip(frames, ts)):
                p8, v8 = pose_client.detect_pose_8(
                    frame,
                    "s-stream",
                    ts=t_val,
                    seq=idx + 1,
                    run_hands=(idx >= 2),
                )
                self.assertEqual(len(p8), 8)
                self.assertEqual(len(v8), 8)

            split_pi = SplitClassifierClient(
                vision_backend_url="http://testserver",
                bone_classifier=pi_bone,
                mode="pi-split",
                http_client=vision_client,
            )
            res_pi = split_pi.classify_segment(
                frames,
                ts,
                session_id="s-stream",
                start=0.0,
                end=ts[-1],
                target_seq=len(frames),
            )
            self.assertTrue(res_pi["streaming_used"])
            self.assertEqual(res_pi["inference_executor"], "pi_local")
            self.assertEqual(res_pi["top1_label"], "Dài")

            split_fb = SplitClassifierClient(
                vision_backend_url="http://testserver",
                bone_classifier=None,
                mode="remote-fallback",
                http_client=vision_client,
            )
            res_fb = split_fb.classify_segment(
                frames,
                ts,
                session_id="s-stream",
                start=0.0,
                end=ts[-1],
                target_seq=len(frames),
            )
            self.assertTrue(res_fb["streaming_used"])
            self.assertEqual(res_fb["inference_executor"], "backend_fallback")
            self.assertEqual(res_fb["top1_label"], "Dài")

            # Missing session on backend triggers 404 and transparent .pbl6 fallback
            res_404 = split_pi.classify_segment(
                frames,
                ts,
                session_id="missing-session",
                start=0.0,
                end=ts[-1],
                target_seq=1,
            )
            self.assertFalse(res_404["streaming_used"])
            self.assertEqual(res_404["top1_label"], "Dài")

    def test_slow_inference_stays_on_pi_by_default(self):
        laptop_bone = _fake_bone_classifier()
        vision_app = create_vision_app(
            vision_extractor=_fake_vision_extractor(), bone_classifier=laptop_bone,
        )
        with TestClient(vision_app) as vision_client:
            pi_bone = _fake_bone_classifier(inference_seconds=1.75)
            split_client = SplitClassifierClient(
                "http://testserver", bone_classifier=pi_bone, http_client=vision_client,
            )
            frames, timestamps = _dummy_bgr_frames()
            for _ in range(3):
                result = split_client.classify_frames(frames, timestamps)
                self.assertEqual(result["inference_executor"], "pi_local")
                self.assertFalse(result["fallback_triggered"])
            self.assertEqual(pi_bone.calls, 3)
            self.assertEqual(laptop_bone.calls, 0)
            self.assertEqual(split_client.status()["fallback_threshold_seconds"], 0.0)
            self.assertFalse(split_client.status()["fallback_active"])

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
        direct = bone.infer_from_arrays(arrays)
        pred = bone.infer_from_arrays(decoded, inference_executor="pi_local")
        self.assertEqual(pred["top1_label"], "Dài")
        self.assertEqual(pred["top1_id"], 95)
        self.assertGreater(pred["confidence"], 0.95)
        self.assertAlmostEqual(pred["confidence"], direct["confidence"], places=6)
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

    @unittest.skipUnless(SAMPLE_NPZ.is_file(), "Sample landmark NPZ not present")
    def test_onnx_bone_classifier_parity_with_torch_on_sample_npz(self):
        arrays = deserialize_landmark_arrays(SAMPLE_NPZ.read_bytes())
        torch_clf = BoneClassifier(bundle=DEFAULT_BUNDLE, backend="torch")
        onnx_clf = BoneClassifier(bundle=DEFAULT_BUNDLE, backend="onnx")
        self.assertEqual(torch_clf.runtime_backend, "torch")
        self.assertEqual(onnx_clf.runtime_backend, "onnx")

        res_t = torch_clf.infer_from_arrays(arrays, inference_executor="pi_local")
        res_o = onnx_clf.infer_from_arrays(arrays, inference_executor="pi_local")
        self.assertEqual(res_t["top1_label"], "Dài")
        self.assertEqual(res_o["top1_label"], "Dài")
        self.assertEqual(
            [item["label_id"] for item in res_t["top5"]],
            [item["label_id"] for item in res_o["top5"]],
        )
        self.assertLess(abs(res_t["confidence"] - res_o["confidence"]), 1e-4)

    @unittest.skipUnless(SAMPLE_CLIP.is_file(), "Sample VSL400 clip 014159.mp4 not present")
    def test_real_streaming_extraction_parity_and_speedup_on_014159(self):
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

        vision = VisionExtractor()
        try:
            vision.extract_from_frames(frames, timestamps, fallback_fps=25.0)
            batch_t0 = time.perf_counter()
            _, _, _, _ = vision.extract_from_frames(frames, timestamps, fallback_fps=25.0)
            batch_s = time.perf_counter() - batch_t0

            vision.reset_stream_models()
            entries: list[StreamFrameEntry] = []
            for idx, (bgr, ts_val) in enumerate(zip(frames, timestamps)):
                # First 8 frames simulate leading -0.30s during READY (run_hands=False)
                _, _, pose_res, hand_res, packed, _ = vision.process_stream_frame(
                    bgr,
                    run_hands=(idx >= 8),
                )
                entries.append(
                    StreamFrameEntry(
                        seq=idx + 1,
                        ts=ts_val,
                        bgr=bgr,
                        pose_res=pose_res,
                        hand_res=hand_res,
                        packed=packed,
                    )
                )

            arrays, qc, crop_rescue, post_s, catchup = vision.extract_from_stream_entries(
                entries,
                fallback_fps=25.0,
            )
        finally:
            vision.close()

        onnx_clf = BoneClassifier(bundle=DEFAULT_BUNDLE, backend="onnx")
        pred = onnx_clf.infer_from_arrays(arrays, inference_executor="pi_local")
        self.assertEqual(pred["top1_label"], "Dài")
        self.assertGreater(pred["confidence"], 0.90)
        self.assertEqual(catchup, 8)
        self.assertLess(post_s, batch_s * 0.5)
        print(
            f"\n[Streaming+ONNX Parity 014159.mp4] top1={pred['top1_label']} ({pred['confidence']:.4f}) "
            f"batch_post={batch_s:.3f}s stream_post={post_s:.3f}s catchup_frames={catchup} "
            f"onnx_infer={pred['inference_seconds']:.3f}s crop={crop_rescue}"
        )


class LinuxCameraProbeTests(unittest.TestCase):
    def test_live_pose_metrics_reports_fifo_http_and_laptop_timings(self):
        frame = np.zeros((16, 16, 3), dtype=np.uint8)
        capture = mock.Mock()
        capture.read.return_value = (True, frame)
        third_request = threading.Event()
        extractor = VisionExtractor()
        model = mock.Mock()
        model.process.return_value = None
        vision_app = create_vision_app(vision_extractor=extractor, enable_fallback_classifier=False)

        with (
            mock.patch.object(extractor, "_ensure_models_unlocked", return_value=(model, model)),
            TestClient(vision_app) as vision,
        ):
            def respond(request: httpx.Request) -> httpx.Response:
                if request.url.path.endswith("/pose-frame"):
                    self.assertEqual(request.url.params["measure"], "1")
                    seq = int(request.url.params["seq"])
                    if seq == 2:
                        return httpx.Response(503)
                response = vision.request(
                    request.method, str(request.url), content=request.content,
                )
                if request.url.params.get("seq") == "3":
                    third_request.set()
                return response

            with httpx.Client(transport=httpx.MockTransport(respond)) as http:
                remote = RemotePoseClient("http://testserver", http_client=http)
                edge_app = create_app(
                    classifier_fn=lambda *_: {},
                    pose_provider=remote.detect_pose_8,
                    on_capture_start=remote.reset,
                    measure_pose=True,
                )
                with (
                    mock.patch.object(edge_app.state.manager, "_open_capture", return_value=capture),
                    TestClient(edge_app) as edge,
                ):
                    self.assertEqual(edge.get("/api/metrics/pose").status_code, 409)
                    started = edge.post("/api/session/start").json()
                    self.assertTrue(started["ok"])
                    self.assertTrue(third_request.wait(timeout=3))
                    self.assertEqual(edge.post("/api/session/stop").status_code, 200)
                    summary = edge.get("/api/metrics/pose").json()
                    self.assertNotIn("frames", summary)
                    report = edge.get("/api/metrics/pose?include_frames=1").json()

        self.assertEqual(report["session_id"], started["session_id"])
        self.assertEqual(report["target_capture_fps"], 25)
        counts = report["counts"]
        self.assertEqual(counts["captured"], counts["dequeued"] + counts["discarded_at_stop"] + counts["dropped_before_send"])
        self.assertEqual(counts["sent"], counts["pose_replies"] + counts["pose_errors"])
        self.assertEqual(counts["in_flight"], 0)
        self.assertEqual(counts["pose_errors"], 1)
        self.assertEqual([frame["seq"] for frame in report["frames"]], list(range(1, counts["sent"] + 1)))
        self.assertEqual(report["frames"][1]["http_status"], 503)
        metrics = report["successful_frame_timings_ms"]
        for key in ("fifo_ms", "encode_ms", "http_ms", "frame_age_ms", "laptop_decode_ms",
                    "laptop_worker_wait_ms", "laptop_mediapipe_lock_wait_ms", "laptop_mediapipe_ms"):
            self.assertEqual(metrics[key]["n"], counts["pose_replies"])
            self.assertGreaterEqual(metrics[key]["p95"], metrics[key]["p50"])

    def test_slow_pose_drops_stale_frames_and_discards_stale_response(self):
        requested_sequences: list[int] = []
        first_requested = threading.Event()
        latest_requested = threading.Event()
        release_first = threading.Event()
        release_latest = threading.Event()

        def respond(request: httpx.Request) -> httpx.Response:
            seq = int(request.url.params["seq"])
            requested_sequences.append(seq)
            if seq == 1:
                first_requested.set()
                release_first.wait(timeout=5)
            elif seq == 5:
                latest_requested.set()
                release_latest.wait(timeout=5)
            return httpx.Response(200, json={"pose": [[0.0, 0.0, 0.0]] * 8, "visibility": [0.0] * 8})

        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            remote_pose = RemotePoseClient("http://testserver", http_client=client)
            manager = LiveSessionManager(classifier_fn=lambda *_: {}, pose_provider=remote_pose.detect_pose_8)
            session_id = manager.start_manual_session()
            consumer = threading.Thread(target=manager._pose_consumer_loop, args=(session_id, manager._epoch), daemon=True)
            frame = np.zeros((16, 16, 3), dtype=np.uint8)

            def publish_capture(seq: int) -> None:
                with manager._pose_cond:
                    while len(manager._pose_frames) >= 1:
                        manager._pose_frames.popleft()
                    manager._pose_frames.append((seq, seq / 10, frame))
                    manager._pose_cond.notify_all()

            consumer.start()
            try:
                publish_capture(1)
                self.assertTrue(first_requested.wait(timeout=2))
                for seq in range(2, 6):
                    publish_capture(seq)
                self.assertEqual(requested_sequences, [1])
                release_first.set()
                self.assertTrue(latest_requested.wait(timeout=2))
                self.assertEqual(requested_sequences, [1, 5])
                self.assertEqual(manager._last_streamed_seq, 1)

                publish_capture(6)
                manager.stop_session(wait_timeout=5)
                self.assertFalse(manager._pose_frames)
                manager.start_manual_session()
                release_latest.set()
                consumer.join(timeout=2)
                self.assertFalse(consumer.is_alive())
                self.assertEqual(manager._last_streamed_seq, 0)
                self.assertIsNone(manager._segmenter.last)
                self.assertEqual(requested_sequences, [1, 5])
            finally:
                release_first.set()
                release_latest.set()
                manager.stop_session(wait_timeout=5)
                consumer.join(timeout=2)

    def test_slow_pose_never_blocks_camera_reads(self):
        release_pose = threading.Event()
        kept_reading = threading.Event()
        read_count = 0
        frame = np.zeros((16, 16, 3), dtype=np.uint8)

        def read_frame():
            nonlocal read_count
            read_count += 1
            if read_count >= 5:
                kept_reading.set()
            time.sleep(0.01)
            return True, frame

        def slow_pose(_frame, _session_id):
            release_pose.wait(timeout=5)
            return [[0.0, 0.0, 0.0]] * 8, [0.0] * 8

        manager = LiveSessionManager(
            classifier_fn=lambda *_: {}, pose_provider=slow_pose, measure_pose=True,
        )
        capture = mock.Mock()
        capture.read.side_effect = read_frame
        with (
            mock.patch("deployment.m2.pipeline.MAX_PENDING_POSE_FRAMES", 1),
            mock.patch.object(manager, "_open_capture", return_value=capture),
        ):
            try:
                manager.start_camera_session()
                self.assertTrue(kept_reading.wait(timeout=2))
                self.assertLessEqual(len(manager._pose_frames), 1)
                self.assertGreaterEqual(read_count, 5)
            finally:
                release_pose.set()
                manager.stop_session(wait_timeout=5)

        report = manager.pose_metrics.report(include_frames=False)
        self.assertEqual(report["fifo_peak_pending"], 1)
        self.assertGreater(report["counts"]["dropped_before_send"], 0)

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

    def test_transient_pose_errors_require_3_frames_and_auto_clear(self):
        events: list[dict] = []
        service = LiveSessionManager(classifier_fn=lambda *_a, **_k: {}, on_event=events.append)
        service._reset_session_state()
        epoch = service._epoch
        bgr = np.zeros((16, 16, 3), dtype=np.uint8)
        calls = 0

        def flaky_pose(_frame, **_kwargs):
            nonlocal calls
            calls += 1
            if calls <= 3:
                raise TimeoutError("timed out")
            return [[0.5, 0.5, 0.0]] * 8, [0.95] * 8

        try:
            last_emit = -10.0
            for _ in range(2):
                _, last_emit = service._estimate_arm_states(flaky_pose, bgr, last_emit, epoch=epoch)
                self.assertIsNone(service.snapshot()["last_error"])

            _, last_emit = service._estimate_arm_states(flaky_pose, bgr, last_emit, epoch=epoch)
            err = service.snapshot()["last_error"] or ""
            self.assertIn("Vision Backend", err)
            self.assertIn("phản hồi chậm", err)

            _, last_emit = service._estimate_arm_states(flaky_pose, bgr, last_emit, epoch=epoch, seq=4)
            self.assertIsNone(service.snapshot()["last_error"])
            self.assertTrue(any(ev.get("type") == "error_cleared" for ev in events))
        finally:
            with service._state_lock:
                service._running = False

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

    def test_live_pipeline_smart_gating_passes_stream_kwargs(self):
        seen_calls: list[dict] = []
        cls_calls: list[dict] = []

        def fake_pose(_bgr, _sid, *, ts=None, seq=None, run_hands=False):
            idx = len(seen_calls)
            seen_calls.append({"ts": ts, "seq": seq, "run_hands": run_hands})
            # shoulder_y=0.2, hip_y=0.6 -> torso=0.4 (rest requires wrist>=0.54 and elbow>=0.32)
            # 0..11 rest (>=0.55s -> READY), 12..28 active (>=0.80s -> onset & CAPTURING), >=29 rest (END_PENDING -> complete)
            is_active = 12 <= idx <= 28
            pose = [
                [0.5, 0.2, 0.0],
                [0.5, 0.2, 0.0],
                [0.5, 0.25 if is_active else 0.45, 0.0],
                [0.5, 0.45, 0.0],
                [0.5, 0.1 if is_active else 0.65, 0.0],
                [0.5, 0.65, 0.0],
                [0.5, 0.6, 0.0],
                [0.5, 0.6, 0.0],
            ]
            return pose, [0.95] * 8

        def fake_cls(frames, timestamps, *, session_id=None, start=None, end=None, target_seq=None):
            cls_calls.append({
                "session_id": session_id,
                "start": start,
                "end": end,
                "target_seq": target_seq,
                "n_frames": len(frames),
            })
            return {
                "top1_label": "Dài",
                "top1_id": 95,
                "confidence": 0.99,
                "low_confidence": False,
                "top5": [{"label": "Dài", "label_id": 95, "score": 0.99}],
                "preprocessing_seconds": 0.05,
                "inference_seconds": 0.02,
                "streaming_used": True,
                "catchup_hands_frames": 3,
                "inference_backend": "onnx",
                "source_frames": len(frames),
            }

        service = LiveSessionManager(classifier_fn=fake_cls, pose_provider=fake_pose)
        dummy = np.full((64, 64, 3), 50, dtype=np.uint8)

        class _StepCap:
            def isOpened(self) -> bool:
                return True

            def set(self, *_args) -> bool:
                return True

            def get(self, *_args) -> float:
                return 20.0

            def read(self):
                time.sleep(0.05)
                return True, dummy

            def release(self) -> None:
                pass

        with mock.patch.object(service, "_open_capture", return_value=_StepCap()):
            service.start_camera_session(camera_index=0)
            deadline = time.monotonic() + 5.0
            while len(cls_calls) == 0 and time.monotonic() < deadline:
                time.sleep(0.05)
            snap = service.stop_session(wait_timeout=3.0)

        self.assertGreaterEqual(len(seen_calls), 25)
        self.assertTrue(all(c["ts"] is not None and c["seq"] is not None for c in seen_calls))
        self.assertFalse(seen_calls[0]["run_hands"])
        self.assertTrue(any(c["run_hands"] for c in seen_calls))
        self.assertEqual(len(cls_calls), 1)
        self.assertTrue(cls_calls[0]["session_id"])
        self.assertGreater(cls_calls[0]["target_seq"], 0)
        self.assertTrue(snap["glosses"][0]["timing"]["streaming_used"])
        self.assertEqual(snap["glosses"][0]["timing"]["inference_backend"], "onnx")


if __name__ == "__main__":
    unittest.main()
