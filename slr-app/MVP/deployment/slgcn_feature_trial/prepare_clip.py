"""Prepare legacy normalized features for the frozen SL-GCN bone checkpoint.

No model loading, training or recognition. Vendor mathematics are unchanged.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import importlib.util
import json
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parent
ADAPTER_SHA = "d4ef152c29aab4986fff558a105abfdf3382055dd9c2e90b1d2aee158c8f5bd8"
REPAIR_SHA = "065fd21c4179524805d580ee1036f8a8f62096a85e73c1f24bca001023ea1bbe"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def training_sources():
    adapter_path = ROOT / "vendor/slgcn_xy_adapter.py"
    repair_path = ROOT / "vendor/team_repair.py"
    require(sha(adapter_path) == ADAPTER_SHA, "Training adapter SHA256 mismatch")
    require(sha(repair_path) == REPAIR_SHA, "Training repair SHA256 mismatch")
    config = json.loads((ROOT / "reference/training_config.json").read_text(encoding="utf-8"))
    require(config["adapter_sha256"] == ADAPTER_SHA, "Unexpected adapter in training config")
    policy = config["adapter_policy"]
    require(policy["repair_sha256"] == REPAIR_SHA, "Unexpected repair in training config")
    require(policy["cache_frames"] == 150 and policy["edge_policy"] == "nan"
            and policy["max_gap"] == 5 and policy["wrist_threshold"] == 1.0,
            "Unexpected frozen temporal/quality policy")
    return (module_at("frozen_slgcn_adapter", adapter_path),
            module_at("frozen_slgcn_repair", repair_path), policy)


def read_features(path):
    with np.load(path, allow_pickle=False) as archive:
        # Training NPZs also have scalar meta_* strings: keep only model features.
        keys = ("upper_body", "left_hand_local", "right_hand_local",
                "left_palm_body", "right_palm_body", "hand_scales",
                "detection_masks", "handedness_valid", "frame_indices", "timestamps")
        missing = set(keys) - set(archive.files)
        require(not missing, "Expected OLD normalized features; missing: " + str(sorted(missing)))
        return {key: archive[key].copy() for key in keys}


def validate_features(features):
    require("upper_body" in features, "Expected legacy normalized upper_body, not Revamped raw")
    count = len(features["upper_body"])
    require(count > 0, "Empty input")
    shapes = {"upper_body": (count, 7, 2),
              "left_hand_local": (count, 21, 2), "right_hand_local": (count, 21, 2),
              "left_palm_body": (count, 5, 2), "right_palm_body": (count, 5, 2),
              "hand_scales": (count, 2), "detection_masks": (count, 4),
              "handedness_valid": (count, 2), "frame_indices": (count,),
              "timestamps": (count,)}
    for key, shape in shapes.items():
        require(key in features, "Missing legacy feature: " + key)
        array = features[key]
        require(array.shape == shape, "Unexpected shape: " + key)
        require(np.issubdtype(array.dtype, np.number) or array.dtype == bool,
                "Non-numeric feature: " + key)
        require(not np.iscomplexobj(array) and not np.isinf(array).any(),
                "Complex/Inf feature: " + key)
    for key in ("detection_masks", "handedness_valid"):
        require(np.isin(features[key], [0, 1]).all(), "Invalid mask: " + key)
    for key in ("frame_indices", "timestamps"):
        array = features[key]
        require(np.isfinite(array).all() and (np.diff(array) > 0).all(),
                "Source sequence must be finite and increasing: " + key)
    index = features["frame_indices"]
    require(np.equal(index, np.floor(index)).all(), "Fractional frame index")
    scales = features["hand_scales"]
    require((scales[np.isfinite(scales)] > 0).all(), "Non-positive hand scale")
    # Same reconstruction check and tolerance used by the frozen training helper.
    max_error = 0.0
    for side_index, side in enumerate(("left", "right")):
        hand = (features[side + "_hand_local"] * scales[:, side_index, None, None]
                + features[side + "_palm_body"][:, :1])
        palm = features[side + "_palm_body"]
        reconstructed = hand[:, [0, 5, 9, 13, 17]]
        good = np.isfinite(reconstructed).all(-1) & np.isfinite(palm).all(-1)
        if good.any():
            error = float(np.max(np.abs(reconstructed[good] - palm[good])))
            require(error <= 1e-5, "Palm reconstruction differs from training schema")
            max_error = max(max_error, error)
    return count, max_error


def prepare_arrays(features, allow_training_truncation=False):
    count, palm_error = validate_features(features)
    require(count <= 150 or allow_training_truncation,
            "Input exceeds 150 frames; explicit --allow-training-truncation is required")
    adapter, repair, policy = training_sources()
    output = adapter.convert(features, repair._repair_array,
                             policy["edges_parent_child"], policy["wrist_threshold"])
    tensor = adapter.prepare_input(output["bone"], output["bone_valid"], 0, 150)[None]
    require(tensor.shape == (1, 2, 150, 27, 1) and tensor.dtype == np.float32,
            "Unexpected final model input")
    require(np.isfinite(tensor).all() and np.any(tensor), "Empty/nonfinite model input")
    require(output["available"][:, 7:].any(), "No usable hand in input")
    require(not (output["available"] & output["quality_blocked"]).any(),
            "Quality-rejected coordinates were filled")
    output["palm_reconstruction_max_abs_error"] = palm_error
    return tensor, output


def verify_bundle():
    manifest = json.loads((ROOT / "bundle_manifest.json").read_text(encoding="utf-8"))
    for name, digest in manifest["sha256"].items():
        require(sha(ROOT / name) == digest, "Bundle SHA256 mismatch: " + name)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path)
    parser.add_argument("--allow-training-truncation", action="store_true")
    args = parser.parse_args()
    verify_bundle()
    from verify_reference import check_references
    references = check_references()
    print("Training source SHA256: OK", flush=True)
    print("Two TRAIN reference samples: exact cached bone/mask match", flush=True)
    if args.features is None:
        latest = ROOT.parent / "feature_extract/latest_result.json"
        require(latest.is_file(), "Missing feature_extract/latest_result.json; use --features")
        record = json.loads(latest.read_text(encoding="utf-8"))
        features_path = Path(record["output_dir"]) / "features_raw.npz"
    else:
        features_path = args.features.resolve()
    metadata_path = features_path.parent / "metadata.json"
    capture_path = features_path.parent / "capture_read_complete_seconds.npy"
    require(features_path.is_file() and metadata_path.is_file() and capture_path.is_file(),
            "Missing feature export or its metadata/capture timing file")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    require(metadata["status"] in ("success", "success_with_warning"), "Feature export failed")
    require(metadata["source_metadata"]["preprocessing_version"] == "1.1.0",
            "Unexpected feature preprocessing version")
    started = time.perf_counter()
    features = read_features(features_path)
    require(metadata["decoded_frames"] == len(features["upper_body"]), "Frame count mismatch")
    capture = np.load(capture_path, allow_pickle=False)
    require(capture.shape == (len(features["upper_body"]),) and np.isfinite(capture).all()
            and (np.diff(capture) > 0).all(), "Invalid original capture timing")
    tensor, output = prepare_arrays(features, args.allow_training_truncation)
    elapsed = time.perf_counter() - started
    destination = ROOT / "results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    destination.mkdir(parents=True, exist_ok=False)
    np.save(destination / "input_tensor.npy", tensor, allow_pickle=False)
    arrays = {key: value for key, value in output.items() if isinstance(value, np.ndarray)}
    arrays["capture_read_complete_seconds_source"] = capture
    arrays["capture_read_complete_seconds_selected"] = capture[output["source_indices"]]
    np.savez_compressed(destination / "adapter_debug.npz", **arrays)
    require(np.array_equal(np.load(destination / "input_tensor.npy", allow_pickle=False), tensor),
            "Saved input tensor differs")
    report = {"status": "PASS_ADAPTER_ONLY", "numpy": np.__version__,
              "input_features": str(features_path), "input_features_sha256": sha(features_path),
              "feature_metadata_sha256": sha(metadata_path), "capture_times_sha256": sha(capture_path),
              "source_video_sha256": metadata["video_sha256"],
              "adapter_sha256": ADAPTER_SHA, "repair_sha256": REPAIR_SHA,
              "training_reference_checks": references,
              "input_shape": list(tensor.shape), "dtype": str(tensor.dtype), "finite": True,
              "source_frames": len(features["upper_body"]),
              "repeated_frames": max(0, 150 - len(features["upper_body"])),
              "truncated_frames": max(0, len(features["upper_body"]) - 150),
              "temporal_policy": "Frozen training policy: repeat indices modulo T below150; first150 above150 only with explicit opt-in. No time resampling.",
              "source_header_timestamps_first_last": features["timestamps"][[0, -1]].tolist(),
              "source_capture_read_times_first_last": capture[[0, -1]].tolist(),
              "timestamp_warning": "Legacy header times and actual capture read-completion times differ. Both preserved. Neither is a sensor exposure timestamp; repeated selected times are not a new live timeline.",
              "adapter_seconds_including_input_read": elapsed,
              "geometry_blocked_selected_frames": int(output["geometry_blocked"].sum()),
              "missing_before_pct": output["missing_before_pct"],
              "missing_after_pct": output["missing_after_pct"],
              "palm_reconstruction_max_abs_error": output["palm_reconstruction_max_abs_error"],
              "warnings": output["warnings"],
              "limitations": "No classifier or sign prediction. Two train-reference matches are not full-dataset parity, accuracy or CPU/GPU logit parity. Current camera clip is unlabeled framing/motion input, not a sign accuracy test."}
    (destination / "metadata.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (ROOT / "latest_result.json").write_text(json.dumps({"output_dir": str(destination)}, indent=2) + "\n", encoding="utf-8")
    print("Model input:", tuple(tensor.shape), "float32 | finite", flush=True)
    print("Frames: source=", report["source_frames"], "repeated=", report["repeated_frames"], flush=True)
    print("PASS: adapter only; classifier NOT run", flush=True)
    print("Results:", destination, flush=True)


if __name__ == "__main__":
    main()
