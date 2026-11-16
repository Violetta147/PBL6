"""Automated verification suite for `segmentation` module invariants and edge cases."""

from __future__ import annotations

import pathlib
import sys
import unittest
from typing import Any

import numpy as np

MVP_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(MVP_ROOT) not in sys.path:
    sys.path.insert(0, str(MVP_ROOT))

from deployment.slgcn_feature_trial.prepare_clip import validate_features  # noqa: E402
from desktop_mvp.check_clip import ClipRecognizer  # noqa: E402
from segmentation import (  # noqa: E402
    SegmentationConfig,
    SequenceSplitConfig,
    build_multi_crop_bounds,
    compute_kinematic_signals,
    detect_single_sign_bounds,
    hybrid_multi_crop_infer,
    make_slgcn_infer_fn,
    slice_feature_arrays,
    sliding_window_infer,
    split_sign_sequence,
    trim_single_sign,
)
from segmentation.compare_timed_rest import settings, tolerate_rest_interruptions  # noqa: E402


class TimedRestTests(unittest.TestCase):
    def test_bridges_only_short_activity_inside_sufficient_rest(self):
        active = np.array([True] * 4 + [False] * 5 + [True] * 2 + [False] * 5 + [True] * 4)
        original = active.copy()
        filtered = tolerate_rest_interruptions(active, fps=15)
        np.testing.assert_array_equal(active, original)
        self.assertFalse(filtered[9:11].any())
        self.assertTrue(filtered[:4].all() and filtered[-4:].all())
        hold = np.ones(30, dtype=bool)
        np.testing.assert_array_equal(tolerate_rest_interruptions(hold, fps=15), hold)
        silence = np.zeros(30, dtype=bool)
        np.testing.assert_array_equal(tolerate_rest_interruptions(silence, fps=15), silence)

    def test_duration_rules_scale_only_the_offline_configuration(self):
        arms = settings(97 / 13)
        self.assertEqual((arms["baseline"]["cfg"].k_off, arms["baseline"]["cfg"].min_segment_frames), (8, 20))
        self.assertEqual((arms["duration_only"]["cfg"].k_off, arms["duration_only"]["cfg"].min_segment_frames), (4, 10))


def _concat_feature_chunks(
    chunks: list[dict[str, np.ndarray]],
    dt: float = 1.0 / 25.0,
) -> dict[str, np.ndarray]:
    """Concatenate feature dicts preserving valid `frame_indices` and `timestamps`."""
    if not chunks:
        raise ValueError("chunks must be non-empty")
    out: dict[str, np.ndarray] = {}
    keys = list(chunks[0].keys())
    for key in keys:
        if key == "frame_indices":
            parts = []
            offset = 0
            for chunk in chunks:
                n = len(chunk["upper_body"])
                parts.append(np.arange(offset, offset + n, dtype=np.int32))
                offset += n
            out[key] = np.concatenate(parts, axis=0)
        elif key == "timestamps":
            parts = []
            t0 = 0.0
            for chunk in chunks:
                n = len(chunk["upper_body"])
                parts.append((t0 + np.arange(n, dtype=np.float64) * dt).astype(np.float32))
                t0 += n * dt
            out[key] = np.concatenate(parts, axis=0)
        else:
            out[key] = np.concatenate([chunk[key] for chunk in chunks], axis=0)
    return out


def _make_rest_chunk(
    template: dict[str, np.ndarray],
    num_frames: int,
    mode: str = "hands_down",
    source_frame_idx: int = 0,
) -> dict[str, np.ndarray]:
    """Build a valid rest gap from a real template frame (`hands_down` or `dropped`)."""
    T_src = len(template["upper_body"])
    idx = max(0, min(int(source_frame_idx), T_src - 1))
    gap: dict[str, np.ndarray] = {}
    for key, val in template.items():
        if key == "frame_indices":
            gap[key] = np.arange(num_frames, dtype=np.int32)
        elif key == "timestamps":
            gap[key] = (np.arange(num_frames, dtype=np.float64) / 25.0).astype(np.float32)
        elif key == "detection_masks":
            masks = np.repeat(val[idx : idx + 1], num_frames, axis=0).copy()
            if mode == "dropped":
                masks[:, 2] = False
                masks[:, 3] = False
            gap[key] = masks
        elif key == "handedness_valid":
            hv = np.repeat(val[idx : idx + 1], num_frames, axis=0).copy()
            if mode == "dropped":
                hv[...] = False
            gap[key] = hv
        elif isinstance(val, np.ndarray) and val.ndim >= 1 and len(val) == T_src:
            arr = np.repeat(val[idx : idx + 1], num_frames, axis=0).copy()
            if mode == "dropped" and key in (
                "left_hand_local",
                "right_hand_local",
                "left_palm_body",
                "right_palm_body",
                "left_hand_body_relations",
                "right_hand_body_relations",
                "hand_scales",
            ):
                arr[...] = np.nan
            gap[key] = arr
        else:
            gap[key] = val.copy() if isinstance(val, np.ndarray) else val
    return gap


def _make_synthetic_hold_clip(
    template: dict[str, np.ndarray],
    *,
    lead_rest: int = 12,
    raise_frames: int = 8,
    hold_frames: int = 36,
    lower_frames: int = 8,
    trail_rest: int = 12,
    y_rest_val: float = 1.65,
    y_hold_val: float = 0.50,
) -> dict[str, np.ndarray]:
    """Build a synthetic clip containing an explicit zero-velocity elevated hold phase."""
    T = lead_rest + raise_frames + hold_frames + lower_frames + trail_rest
    arr = _make_rest_chunk(template, T, mode="hands_down", source_frame_idx=0)
    arr["detection_masks"][:, 0] = True
    arr["detection_masks"][:, 2] = True
    arr["detection_masks"][:, 3] = True

    # Start clean rest coordinates from resting pose; force wrists above/below y_rest explicitly
    profile_y = np.empty(T, dtype=np.float32)
    i0 = 0
    profile_y[i0 : i0 + lead_rest] = y_rest_val
    i0 += lead_rest
    profile_y[i0 : i0 + raise_frames] = np.linspace(
        y_rest_val, y_hold_val, raise_frames, dtype=np.float32
    )
    i0 += raise_frames
    # Hold phase: stationary elevated wrists (velocity == 0, y == 0.50 <= 1.15)
    profile_y[i0 : i0 + hold_frames] = y_hold_val
    i0 += hold_frames
    profile_y[i0 : i0 + lower_frames] = np.linspace(
        y_hold_val, y_rest_val, lower_frames, dtype=np.float32
    )
    i0 += lower_frames
    profile_y[i0 : i0 + trail_rest] = y_rest_val

    arr["left_palm_body"][:, :, 1] = profile_y[:, None]
    arr["left_palm_body"][:, :, 0] = 0.25
    arr["right_palm_body"][:, :, 1] = profile_y[:, None]
    arr["right_palm_body"][:, :, 0] = -0.25
    arr["upper_body"][:, 5, 1] = profile_y
    arr["upper_body"][:, 6, 1] = profile_y
    arr["upper_body"][:, 5, 0] = 0.25
    arr["upper_body"][:, 6, 0] = -0.25
    if "handedness_valid" in arr:
        arr["handedness_valid"][:, :] = True
    return arr


class SegmentationTestSuite(unittest.TestCase):
    recognizer: ClipRecognizer
    _infer_fn_holder: list[Any]
    clip_014159_arrays: dict[str, np.ndarray]
    clip_014159_meta: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.recognizer = ClipRecognizer()
        cls._infer_fn_holder = [
            make_slgcn_infer_fn(cls.recognizer, allow_training_truncation=True)
        ]
        clip_path = MVP_ROOT / "local_data" / "014159.mp4"
        if not clip_path.exists():
            raise FileNotFoundError(f"Missing sample clip: {clip_path}")
        extract_res = cls.recognizer.extract_video(clip_path, cls.recognizer.config)
        if extract_res.error or extract_res.status not in ("success", "success_with_warning"):
            raise RuntimeError(extract_res.error or f"Extractor failed: {extract_res.status}")
        cls.clip_014159_arrays = extract_res.arrays
        cls.clip_014159_meta = {
            "fps": getattr(extract_res, "fps", 25.0),
            "decoded_frames": getattr(extract_res, "decoded_frames", None),
            "status": extract_res.status,
        }

    def setUp(self) -> None:
        self.infer_fn = self._infer_fn_holder[0]

    # --- Invariant (a): validate_features passes 100% after trimming ---
    def test_a_validate_features_after_trimming_and_slicing(self) -> None:
        for mode in ("kinematic_wrist_fsm", "velocity_only"):
            trimmed, bounds = trim_single_sign(
                self.clip_014159_arrays, SegmentationConfig(mode=mode)
            )
            count, max_err = validate_features(trimmed)
            self.assertEqual(count, bounds["trimmed_frames"])
            self.assertLessEqual(max_err, 1e-5)
            self.assertTrue(np.issubdtype(trimmed["frame_indices"].dtype, np.integer))
            self.assertTrue(np.all(np.diff(trimmed["frame_indices"]) > 0))
            self.assertTrue(np.all(np.diff(trimmed["timestamps"]) > 0))

        # Interior slice + high-offset float32 timestamp precision repair test
        mid_slice = slice_feature_arrays(self.clip_014159_arrays, 10, 45)
        count_mid, _ = validate_features(mid_slice)
        self.assertEqual(count_mid, 35)

        degraded = {
            k: (v.copy() if isinstance(v, np.ndarray) else v)
            for k, v in self.clip_014159_arrays.items()
        }
        # Simulate float32 timestamp collision at large recording durations
        degraded["timestamps"] = np.full(
            len(degraded["upper_body"]), 100000.0, dtype=np.float32
        )
        repaired = slice_feature_arrays(degraded, 5, 40)
        count_rep, _ = validate_features(repaired)
        self.assertEqual(count_rep, 35)
        self.assertTrue(np.all(np.diff(repaired["timestamps"]) > 0))

    # --- Invariant (b): 014159.mp4 preserves >= 85% and predicts "Dài" > 0.99 ---
    def test_b_single_sign_014159_preserves_and_predicts_dai(self) -> None:
        T = len(self.clip_014159_arrays["upper_body"])
        trimmed, bounds = trim_single_sign(
            self.clip_014159_arrays, SegmentationConfig(mode="kinematic_wrist_fsm")
        )
        validate_features(trimmed)
        self.assertFalse(bounds["fallback_triggered"])
        self.assertGreaterEqual(bounds["kept_ratio"], 0.85)
        self.assertEqual(bounds["trimmed_frames"], trimmed["upper_body"].shape[0])
        self.assertGreater(bounds["t_start"], 0)  # Leading idle frames were trimmed
        self.assertLessEqual(bounds["t_end"], T)

        pred = self.infer_fn(trimmed)
        self.assertEqual(pred["top1_gloss"], "Dài")
        self.assertGreater(pred["top1_softmax"], 0.99)

        # Also check Method 3 Hybrid 3-crop on 014159.mp4
        hyb = hybrid_multi_crop_infer(
            self.clip_014159_arrays,
            bounds,
            self.infer_fn,
            delta=5,
            idx_to_gloss=self.infer_fn.idx_to_gloss,
        )
        self.assertEqual(hyb["num_crops_attempted"], 3)
        self.assertEqual(hyb["num_crops_succeeded"], 3)
        self.assertEqual(hyb["top1_gloss"], "Dài")
        self.assertGreater(hyb["top1_softmax"], 0.99)

    # --- Invariant (c): Ablation - Velocity-Only breaks on hold phase while FSM keeps it ---
    def test_c_hold_phase_ablation_velocity_only_vs_kinematic_fsm(self) -> None:
        # Case 1: Hold phase longer than max_internal_gap (36 frames > gap=5)
        synth = _make_synthetic_hold_clip(
            self.clip_014159_arrays,
            lead_rest=12,
            raise_frames=8,
            hold_frames=36,
            lower_frames=8,
            trail_rest=12,
        )
        # True active motion span: frames [12, 64) -> length 52 frames
        cfg_fsm = SegmentationConfig(mode="kinematic_wrist_fsm", use_fallback_invariant=False)
        cfg_vel = SegmentationConfig(mode="velocity_only", use_fallback_invariant=False)

        b_fsm = detect_single_sign_bounds(synth, cfg_fsm)
        b_vel = detect_single_sign_bounds(synth, cfg_vel)

        # Hold indices are [20, 56). FSM must retain the full hold phase as 1 connected sign.
        self.assertEqual(b_fsm["num_components"], 1)
        self.assertLessEqual(b_fsm["raw_t_start"], 13)
        self.assertGreaterEqual(b_fsm["raw_t_end"], 62)
        self.assertGreaterEqual(b_fsm["trimmed_frames"], 50)

        # Velocity-only splits the sign across the zero-velocity hold gap into fragmented/small motion peaks
        self.assertGreaterEqual(b_vel["num_components"], 2)
        self.assertLess(b_vel["raw_t_end"] - b_vel["raw_t_start"], 15)
        self.assertLess(b_vel["trimmed_frames"], 20)

        # Even with fallback invariant enabled, Velocity-Only fails to detect a >=24f component and falls back to full clip
        b_vel_fb = detect_single_sign_bounds(
            synth, SegmentationConfig(mode="velocity_only", use_fallback_invariant=True)
        )
        self.assertTrue(b_vel_fb["fallback_triggered"])

        # Case 2: Stationary held posture with zero motion throughout
        stationary = _make_synthetic_hold_clip(
            self.clip_014159_arrays,
            lead_rest=10,
            raise_frames=0,
            hold_frames=40,
            lower_frames=0,
            trail_rest=10,
        )
        b_stat_fsm = detect_single_sign_bounds(
            stationary, SegmentationConfig(mode="kinematic_wrist_fsm", use_fallback_invariant=False)
        )
        b_stat_vel = detect_single_sign_bounds(
            stationary, SegmentationConfig(mode="velocity_only", use_fallback_invariant=False)
        )
        self.assertGreaterEqual(b_stat_fsm["raw_t_end"] - b_stat_fsm["raw_t_start"], 40)
        self.assertEqual(b_stat_vel["active_raw_frames"], 0)
        self.assertEqual(b_stat_vel["num_components"], 0)

    # --- Invariant (d): Concatenated 3x 014159 + 20 rest/dropped-hand frames ---
    def test_d_concatenated_multi_sign_sequence_extracts_3_dai_segments(self) -> None:
        base = self.clip_014159_arrays
        for gap_mode in ("hands_down", "dropped"):
            with self.subTest(gap_mode=gap_mode):
                gap = _make_rest_chunk(base, 20, mode=gap_mode, source_frame_idx=0)
                seq = _concat_feature_chunks([base, gap, base, gap, base], dt=1.0 / 25.0)
                validate_features(seq)

                res = split_sign_sequence(seq, SequenceSplitConfig(), infer_fn=self.infer_fn)
                self.assertEqual(
                    res["num_segments"],
                    3,
                    msg=f"Expected 3 segments for gap_mode={gap_mode}, got {res['num_segments']}",
                )
                for idx, seg in enumerate(res["segments"]):
                    self.assertIsNone(
                        seg["error"],
                        msg=f"Segment {idx} failed inference: {seg['error']}",
                    )
                    validate_features(seg["arrays"])
                    self.assertEqual(seg["prediction"]["top1_gloss"], "Dài")
                    self.assertGreater(seg["prediction"]["top1_softmax"], 0.99)

    # --- Edge Cases: short, empty, all-NaN, >150 frames, sliding window, multi-crop ---
    def test_edge_cases_and_apis(self) -> None:
        # 1. Empty sequence raises ValueError cleanly
        empty = {
            k: (v[:0] if isinstance(v, np.ndarray) and v.ndim >= 1 else v)
            for k, v in self.clip_014159_arrays.items()
        }
        with self.assertRaises(ValueError):
            trim_single_sign(empty)
        with self.assertRaises(ValueError):
            split_sign_sequence(empty)
        with self.assertRaises(ValueError):
            sliding_window_infer(empty, self.infer_fn)

        # 2. All-NaN / zero hands (H=0) triggers fallback in single-sign mode and 0 segments in splitter
        no_hand = _make_rest_chunk(self.clip_014159_arrays, 40, mode="dropped")
        b_nohand = detect_single_sign_bounds(no_hand)
        self.assertTrue(b_nohand["fallback_triggered"])
        self.assertEqual(b_nohand["fallback_reason"], "no_active_frames")
        self.assertEqual((b_nohand["t_start"], b_nohand["t_end"]), (0, 40))
        sp_nohand = split_sign_sequence(no_hand)
        self.assertEqual(sp_nohand["num_segments"], 0)

        # 3. >150-frame active clip is capped safely at max_output_frames=150 for prepare_arrays
        long_seq = _concat_feature_chunks([self.clip_014159_arrays] * 4)
        # Repeat real active signing frame (index 25) so palm reconstruction stays valid & y_wrist <= y_rest
        long_active = _make_rest_chunk(
            self.clip_014159_arrays, 190, mode="hands_down", source_frame_idx=25
        )
        trimmed_long, b_long = trim_single_sign(long_active)
        self.assertEqual(b_long["trimmed_frames"], 150)
        validate_features(trimmed_long)
        self.assertEqual(len(long_seq["upper_body"]), 236)

        # 4. Pure Sliding Window W=60, S=15 on 2-sign sequence + 25 dropped frames
        gap25 = _make_rest_chunk(self.clip_014159_arrays, 25, mode="dropped")
        seq2 = _concat_feature_chunks([self.clip_014159_arrays, gap25, self.clip_014159_arrays])
        sw = sliding_window_infer(
            seq2, self.infer_fn, window_size=60, stride=15, conf_threshold=0.50
        )
        self.assertGreater(sw["num_windows_total"], 4)
        self.assertGreaterEqual(sw["num_windows_evaluated"], 4)
        self.assertGreaterEqual(sw["num_detections"], 2)

        # 5. build_multi_crop_bounds respects boundaries & min_crop_frames
        crops = build_multi_crop_bounds(20, 80, total_frames=120, delta=5, min_crop_frames=20)
        self.assertEqual(crops, [("tight", 25, 75), ("nominal", 20, 80), ("wide", 15, 85)])

        # 6. hybrid_multi_crop_infer tolerates single failing shifted crop as long as nominal succeeds
        calls = {"n": 0}

        def flaky_infer(sub: dict[str, np.ndarray]) -> dict[str, Any]:
            calls["n"] += 1
            if calls["n"] == 1:
                raise ValueError("Simulated geometry block on tight crop")
            return self.infer_fn(sub)

        hyb_partial = hybrid_multi_crop_infer(
            self.clip_014159_arrays, (6, 59), flaky_infer, delta=5, idx_to_gloss=self.infer_fn.idx_to_gloss
        )
        self.assertEqual(hyb_partial["num_crops_attempted"], 3)
        self.assertEqual(hyb_partial["num_crops_succeeded"], 2)
        self.assertEqual(hyb_partial["top1_gloss"], "Dài")

        # 7. Short internal pause <= 5 frames inside a sign must NOT split into 2 segments
        sig_brief = compute_kinematic_signals(
            _make_synthetic_hold_clip(
                self.clip_014159_arrays,
                lead_rest=5,
                raise_frames=10,
                hold_frames=25,
                lower_frames=10,
                trail_rest=5,
            )
        )
        self.assertTrue(sig_brief["active_raw"][15:40].all())

        # 8. Invalid slice / config bounds & regression edge cases
        with self.assertRaises(ValueError):
            slice_feature_arrays(self.clip_014159_arrays, 10, 10)
        with self.assertRaises(ValueError):
            SegmentationConfig(mode="unknown_mode")
        with self.assertRaises(ValueError):
            SequenceSplitConfig(k_off=0)
        with self.assertRaises(ValueError):
            SequenceSplitConfig(mode="unknown_mode")
        with self.assertRaises(ValueError):
            SequenceSplitConfig(min_segment_frames=50, max_segment_frames=10)

        # 9. _make_rest_chunk dropped clears real extractor hand arrays + handedness
        dropped10 = _make_rest_chunk(self.clip_014159_arrays, 10, mode="dropped")
        self.assertFalse(np.isfinite(dropped10["left_hand_local"]).any())
        self.assertFalse(np.isfinite(dropped10["right_hand_local"]).any())
        self.assertFalse(dropped10["handedness_valid"].any())
        validate_features(dropped10)

        # 10. T > max_output_frames fallback with late short burst preserves active frames
        late_rest_prefix = _make_rest_chunk(self.clip_014159_arrays, 155, mode="hands_down", source_frame_idx=0)
        late_burst = _make_rest_chunk(self.clip_014159_arrays, 10, mode="hands_down", source_frame_idx=25)
        late_rest_suffix = _make_rest_chunk(self.clip_014159_arrays, 35, mode="hands_down", source_frame_idx=0)
        late_seq = _concat_feature_chunks([late_rest_prefix, late_burst, late_rest_suffix])
        b_late = detect_single_sign_bounds(late_seq)
        self.assertTrue(b_late["fallback_triggered"])
        self.assertLessEqual(b_late["t_start"], 155)
        self.assertGreaterEqual(b_late["t_end"], 165)
        self.assertEqual(b_late["trimmed_frames"], 150)

        # 11. use_fallback_invariant=False on all-rest raises clear ValueError in trim_single_sign
        all_rest = _make_rest_chunk(self.clip_014159_arrays, 40, mode="hands_down", source_frame_idx=0)
        with self.assertRaises(ValueError):
            trim_single_sign(all_rest, SegmentationConfig(use_fallback_invariant=False))

        # 12. split_sign_sequence enforces max_segment_frames <= 150
        long_split = split_sign_sequence(long_active, SequenceSplitConfig(max_segment_frames=150))
        self.assertEqual(long_split["num_segments"], 2)
        for seg in long_split["segments"]:
            self.assertLessEqual(seg["num_frames"], 150)
            self.assertGreaterEqual(seg["num_frames"], 20)
            validate_features(seg["arrays"])

        # 13. sliding_window_infer respects min_window_frames and non-ValueError failures
        short5 = _make_rest_chunk(self.clip_014159_arrays, 5, mode="hands_down", source_frame_idx=25)
        sw_short = sliding_window_infer(short5, self.infer_fn, window_size=60, stride=15, min_window_frames=20)
        self.assertEqual(sw_short["num_windows_evaluated"], 0)
        self.assertEqual(sw_short["num_detections"], 0)

        def err_infer(_: dict[str, np.ndarray]) -> dict[str, Any]:
            raise RuntimeError("Simulated inference crash")

        sw_err = sliding_window_infer(self.clip_014159_arrays, err_infer, window_size=40, stride=15)
        self.assertEqual(sw_err["num_windows_evaluated"], 0)
        self.assertGreater(sw_err["num_windows_skipped"], 0)

        # 14. build_multi_crop_bounds does not mislabel inward trims as 'wide'; fallback skips inward trim
        full_crops = build_multi_crop_bounds(0, 119, total_frames=119, delta=5, min_crop_frames=20)
        self.assertEqual(full_crops, [("tight", 5, 114), ("nominal", 0, 119)])
        fb_hyb = hybrid_multi_crop_infer(
            self.clip_014159_arrays,
            {"t_start": 0, "t_end": 59, "fallback_triggered": True},
            self.infer_fn,
            delta=5,
            idx_to_gloss=self.infer_fn.idx_to_gloss,
        )
        self.assertEqual(fb_hyb["num_crops_attempted"], 1)
        self.assertEqual(fb_hyb["crops"][0]["crop_name"], "nominal")

        # 15. Malformed palm shape raises ValueError & Inf values emit no RuntimeWarning
        bad_shape = dict(self.clip_014159_arrays)
        bad_shape["left_palm_body"] = np.zeros((len(bad_shape["upper_body"]), 2), dtype=np.float32)
        with self.assertRaises(ValueError):
            compute_kinematic_signals(bad_shape)
        inf_arr = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in self.clip_014159_arrays.items()}
        inf_arr["left_palm_body"][10:15, 0, 1] = np.inf
        import warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            compute_kinematic_signals(inf_arr)
        self.assertEqual(len(caught), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
