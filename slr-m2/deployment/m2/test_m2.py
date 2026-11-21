"""Automated verification suite for M2.1 live pipeline, FastAPI/WS contract, and 07b parity."""
from __future__ import annotations

import os
from pathlib import Path
import time
import unittest

import numpy as np
from fastapi.testclient import TestClient

from deployment.m1.common import DEFAULT_BUNDLE, ROOT
from deployment.m2.classifier import SLRClassifier
from deployment.m2.pipeline import LiveSessionManager, load_frozen_config
from deployment.m2.server import DEFAULT_TTS_DIR, create_app

SAMPLE_CLIP = Path(os.environ.get("PBL6_M2_SAMPLE_CLIP", ROOT.parent / "slr-app/MVP/local_data/014159.mp4"))


def _dummy_frame(val: int = 0) -> np.ndarray:
    return np.full((64, 64, 3), val % 255, dtype=np.uint8)


def _fake_classifier_factory(labels: list[tuple[str, int, float]], delay: float = 0.05):
    calls: list[int] = []

    def _classify(frames: list[np.ndarray], timestamps: list[float]) -> dict:
        idx = len(calls)
        calls.append(len(frames))
        if delay > 0:
            time.sleep(delay)
        label, lid, score = labels[min(idx, len(labels) - 1)]
        return {
            "top1_label": label,
            "top1_id": lid,
            "confidence": score,
            "low_confidence": score < 0.50,
            "top5": [{"label": label, "label_id": lid, "score": score}],
            "preprocessing_seconds": delay,
            "inference_seconds": 0.01,
            "source_frames": len(frames),
        }

    return _classify, calls


class M2PipelineTests(unittest.TestCase):
    def test_utterance_resumes_after_half_second_tracking_loss(self):
        published: list[dict] = []
        classifier, _ = _fake_classifier_factory([("Dài", 95, 0.99)], delay=0)
        manager = LiveSessionManager(classifier_fn=classifier, on_event=published.append)
        manager.start_manual_session()
        self.addCleanup(manager.stop_session, wait_timeout=5)
        self.assertEqual(manager.config.utterance_rest, 4.0)

        def feed(step: int):
            if 49 <= step < 53:
                arms = [None, None]
            elif 8 <= step < 18 or 64 <= step < 75:
                arms = ["active", "rest"]
            else:
                arms = ["rest", "rest"]
            return manager.feed_step(step / 10, arms, frame=_dummy_frame())

        # Three seconds of REST, half a second unobserved, then one more second of REST.
        for step in range(63):
            self.assertFalse(any(event.get("type") == "utterance_end" for event in feed(step)))
        self.assertEqual(feed(63), [{"type": "utterance_end", "utterance_id": "0", "timestamp": 6.3}])

        for step in range(64, 115):
            self.assertFalse(any(event.get("type") == "utterance_end" for event in feed(step)))
        self.assertEqual(feed(115), [{"type": "utterance_end", "utterance_id": "1", "timestamp": 11.5}])

        snapshot = manager.stop_session(wait_timeout=5)
        self.assertEqual([item["utterance_id"] for item in snapshot["glosses"]], ["0", "1"])
        self.assertEqual([item["raw_glosses"] for item in snapshot["utterances"]], [["Dài"], ["Dài"]])
        self.assertEqual(
            [event["type"] for event in published if event["type"] in ("gloss_result", "utterance_ready")],
            ["gloss_result", "utterance_ready", "gloss_result", "utterance_ready"],
        )

    def test_utterance_rest_resets_after_long_loss_active_hand_or_timestamp_gap(self):
        for scenario, interruptions, resumed in (
            ("long tracking loss", [(step, [None, None]) for step in range(49, 54)], 54),
            ("one visible active hand", [(49, ["active", None])], 50),
            ("timestamp gap", [], 54),
        ):
            with self.subTest(scenario=scenario):
                classifier, _ = _fake_classifier_factory([("Dài", 95, 0.99)], delay=0)
                manager = LiveSessionManager(classifier_fn=classifier)
                manager.start_manual_session()
                try:
                    observations = [
                        (step, ["active", "rest"] if 8 <= step < 18 else ["rest", "rest"])
                        for step in range(49)
                    ]
                    observations.extend(interruptions)
                    observations.extend((step, ["rest", "rest"]) for step in range(resumed, resumed + 40))
                    for step, arms in observations:
                        events = manager.feed_step(step / 10, arms, frame=_dummy_frame())
                        self.assertFalse(any(event.get("type") == "utterance_end" for event in events))
                    timestamp = (resumed + 40) / 10
                    self.assertEqual(
                        manager.feed_step(timestamp, ["rest", "rest"], frame=_dummy_frame()),
                        [{"type": "utterance_end", "utterance_id": "0", "timestamp": timestamp}],
                    )
                finally:
                    manager.stop_session(wait_timeout=5)

    def test_repeated_signs_keep_order_and_utterance_waits_for_worker(self):
        events: list[dict] = []
        clf, calls = _fake_classifier_factory([("Cảm ơn", 86, 0.96), ("Cảm ơn", 86, 0.91)], delay=0.12)
        mgr = LiveSessionManager(classifier_fn=clf, config=load_frozen_config(), on_event=events.append)
        mgr.start_manual_session()

        # 0.0..0.9s rest -> READY
        # 1.0..2.9s active (sign 1), 3.0..4.0s rest -> seg 1 complete
        # 4.1..5.9s active (sign 2), 6.0..8.0s rest -> seg 2 complete + utterance_end at >= 7.5s
        for i in range(85):
            t = i * 0.1
            active = (10 <= i < 30) or (41 <= i < 60)
            arms = ["active", "rest"] if active else ["rest", "rest"]
            mgr.feed_step(t, arms, frame=_dummy_frame(i))

        snap = mgr.stop_session(wait_timeout=10.0)
        self.assertEqual(len(calls), 2)
        self.assertEqual([g["raw"]["top1_label"] for g in snap["glosses"]], ["Cảm ơn", "Cảm ơn"])
        self.assertNotEqual(snap["glosses"][0]["segment_id"], snap["glosses"][1]["segment_id"])
        self.assertEqual(len(snap["utterances"]), 1)
        self.assertEqual(snap["utterances"][0]["raw_glosses"], ["Cảm ơn", "Cảm ơn"])
        self.assertEqual(snap["utterances"][0]["reason"], "utterance_rest")

        # Verify gloss_result events both preceded utterance_ready in FIFO order.
        types = [e["type"] for e in events if e["type"] in ("gloss_result", "utterance_ready")]
        self.assertEqual(types, ["gloss_result", "gloss_result", "utterance_ready"])

    def test_tracking_loss_never_enqueues_garbage(self):
        clf, calls = _fake_classifier_factory([("Dài", 95, 0.99)], delay=0.01)
        mgr = LiveSessionManager(classifier_fn=clf, config=load_frozen_config())
        mgr.start_manual_session()

        for i in range(35):
            t = i * 0.1
            if i < 10:
                arms = ["rest", "rest"]
            elif i < 20:
                arms = ["active", "rest"]
            else:
                arms = [None, None]
            mgr.feed_step(t, arms, frame=_dummy_frame(i))

        snap = mgr.stop_session(wait_timeout=5.0)
        self.assertEqual(len(calls), 0)
        self.assertEqual(len(snap["glosses"]), 0)
        self.assertEqual(len(snap["incomplete_events"]), 1)
        self.assertEqual(snap["incomplete_events"][0]["reason"], "tracking_loss")

    def test_stop_mid_sign_drains_completed_and_marks_open_incomplete(self):
        clf, calls = _fake_classifier_factory([("Dài", 95, 0.98), ("Nước", 243, 0.32)], delay=0.15)
        mgr = LiveSessionManager(classifier_fn=clf, config=load_frozen_config())
        mgr.start_manual_session()

        # Complete sign 1, start sign 2, then press Stop before sign 2 finishes!
        for i in range(55):
            t = i * 0.1
            if i < 10:
                arms = ["rest", "rest"]
            elif i < 25:
                arms = ["active", "rest"]
            elif i < 35:
                arms = ["rest", "rest"]  # closes seg 1 at 3.0s
            else:
                arms = ["active", "active"]  # seg 2 still open at stop
            mgr.feed_step(t, arms, frame=_dummy_frame(i))

        snap = mgr.stop_session(wait_timeout=10.0)
        self.assertEqual(len(calls), 1)
        self.assertEqual([g["raw"]["top1_label"] for g in snap["glosses"]], ["Dài"])
        self.assertEqual(len(snap["utterances"]), 1)
        self.assertEqual(snap["utterances"][0]["reason"], "session_stop")
        self.assertEqual(len(snap["incomplete_events"]), 1)
        self.assertEqual(snap["incomplete_events"][0]["reason"], "end_of_file")

    def test_low_confidence_flag(self):
        clf, _ = _fake_classifier_factory([("Nước", 243, 0.32)], delay=0.01)
        mgr = LiveSessionManager(classifier_fn=clf, config=load_frozen_config())
        mgr.start_manual_session()
        for i in range(45):
            arms = ["active", "rest"] if 10 <= i < 25 else ["rest", "rest"]
            mgr.feed_step(i * 0.1, arms, frame=_dummy_frame(i))
        snap = mgr.stop_session(wait_timeout=5.0)
        self.assertEqual(len(snap["glosses"]), 1)
        self.assertTrue(snap["glosses"][0]["raw"]["low_confidence"])


class M2ServerContractTests(unittest.TestCase):
    def test_http_and_websocket_snapshot(self):
        clf, _ = _fake_classifier_factory([("Dài", 95, 0.99)], delay=0.01)
        app = create_app(classifier_fn=clf, preload_model=False)
        with TestClient(app) as client:
            health = client.get("/api/health")
            self.assertEqual(health.status_code, 200)
            self.assertEqual(health.json()["status"], "ok")

            state = client.get("/api/state")
            self.assertEqual(state.status_code, 200)
            self.assertEqual(state.json()["schema_version"], "m2.v1")

            with client.websocket_connect("/ws/live") as ws:
                msg = ws.receive_json()
                self.assertEqual(msg["type"], "snapshot")
                self.assertIn("config", msg["snapshot"])

            bad = client.get("/api/tts/999.mp3")
            self.assertEqual(bad.status_code, 404)
            neg = client.get("/api/tts/-1.mp3")
            self.assertEqual(neg.status_code, 404)
            if (DEFAULT_TTS_DIR / "95.mp3").is_file():
                ok_tts = client.get("/api/tts/95.mp3")
                self.assertEqual(ok_tts.status_code, 200)
                self.assertEqual(ok_tts.headers.get("content-type"), "audio/mpeg")


class M2Real07bParityTests(unittest.TestCase):
    @unittest.skipUnless(SAMPLE_CLIP.is_file(), "Sample VSL400 clip 014159.mp4 not present")
    def test_warm_loaded_07b_parity_and_split_stage(self):
        clf = SLRClassifier(bundle=DEFAULT_BUNDLE)
        arrays, qc, crop_rescue, pre_s = clf.extract_landmarks(SAMPLE_CLIP)
        first = clf.infer_from_arrays(arrays)
        second = clf.infer_from_arrays(arrays)

        self.assertEqual(first["top1_label"], "Dài")
        self.assertEqual(first["top1_id"], 95)
        self.assertGreater(first["confidence"], 0.90)
        self.assertFalse(first["low_confidence"])
        self.assertAlmostEqual(first["confidence"], second["confidence"], places=5)
        print(
            f"\n[M2 Parity 014159.mp4] top1={first['top1_label']} ({first['confidence']:.4f}) "
            f"pre={pre_s:.2f}s forward1={first['inference_seconds']:.3f}s "
            f"forward2_warm={second['inference_seconds']:.3f}s crop_rescue={crop_rescue}"
        )


if __name__ == "__main__":
    unittest.main()
