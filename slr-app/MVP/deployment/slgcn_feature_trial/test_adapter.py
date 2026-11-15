"""Meaningful regression checks against historical cached training artifacts."""
import unittest
import numpy as np
from prepare_clip import ROOT, prepare_arrays, read_features, validate_features
from verify_reference import check_references


class AdapterChecks(unittest.TestCase):
    def setUp(self):
        self.features = read_features(ROOT / "reference/training_qc/014615_front.npz")

    def test_two_historical_train_cache_references(self):
        self.assertEqual(len(check_references()), 2)

    def test_revamped_schema_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "legacy"):
            validate_features({"raw_pose_xyz": np.zeros((10, 8, 3))})

    def test_invalid_numeric_input_is_rejected(self):
        self.features["hand_scales"][0, 0] = np.inf
        with self.assertRaisesRegex(ValueError, "Inf"):
            validate_features(self.features)

    def test_malformed_geometry_is_rejected(self):
        self.features["left_palm_body"][:, 1] += 2
        with self.assertRaisesRegex(ValueError, "Palm"):
            validate_features(self.features)

    def test_truncation_requires_explicit_opt_in(self):
        indices = np.arange(151) % len(self.features["upper_body"])
        extended = {key: value[indices].copy() for key, value in self.features.items()}
        extended["frame_indices"] = np.arange(151)
        extended["timestamps"] = np.arange(151, dtype=np.float32) / 30
        with self.assertRaisesRegex(ValueError, "explicit"):
            prepare_arrays(extended)
        tensor, output = prepare_arrays(extended, allow_training_truncation=True)
        self.assertEqual(tensor.shape, (1, 2, 150, 27, 1))
        np.testing.assert_array_equal(output["source_indices"], np.arange(150))

    def test_source_arrays_are_not_modified(self):
        original = {key: value.copy() for key, value in self.features.items()}
        prepare_arrays(self.features)
        for key in original:
            np.testing.assert_array_equal(self.features[key], original[key])


if __name__ == "__main__":
    unittest.main(verbosity=2)
