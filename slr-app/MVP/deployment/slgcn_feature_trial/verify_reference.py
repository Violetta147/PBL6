"""Compare unchanged frozen adapter output to two saved TRAIN QC samples."""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
from prepare_clip import ROOT, prepare_arrays, read_features, require


def check_references():
    folder = ROOT / "reference/training_qc"
    checks = json.loads((folder / "sha256.json").read_text(encoding="utf-8"))
    for name in ("bone_xy.npy", "masks_and_frames.npz", "index_qc.csv", "adapter_config.json"):
        require(hashlib.sha256((folder / name).read_bytes()).hexdigest() == checks[name],
                "Training reference hash differs: " + name)
    with (folder / "index_qc.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    bones = np.load(folder / "bone_xy.npy", allow_pickle=False)
    results = []
    with np.load(folder / "masks_and_frames.npz", allow_pickle=False) as masks:
        for video_id in ("014615", "020536"):
            row = next(row for row in rows if row["video_id"] == video_id)
            require(row["split"] == "train", "Reference is not a train sample")
            index = rows.index(row)
            source = folder / (video_id + "_front.npz")
            require(hashlib.sha256(source.read_bytes()).hexdigest() == row["npz_sha256"],
                    "Original training feature hash differs")
            _, output = prepare_arrays(read_features(source))
            require(np.array_equal(output["bone"], bones[index]), "Bone cache mismatch: " + video_id)
            for key in masks.files:
                require(np.array_equal(output[key], masks[key][index], equal_nan=True),
                        "Cached mask/provenance mismatch: " + video_id + "/" + key)
            # Independent centering check on the SAVED reference bone, not a second adapter call.
            expected = bones[index].copy()
            good = masks["bone_valid"][index, :, 0]
            root = expected[:, :, 0, 0]
            if good.any():
                root[:, good] -= root[:, good].mean(axis=1, keepdims=True)
            root[:, ~good] = 0
            actual, _ = prepare_arrays(read_features(source))
            require(np.array_equal(actual[0], expected), "Final root-centering mismatch")
            results.append({"video_id": video_id, "split": "train", "bone_max_abs_diff": 0.0,
                            "saved_masks_and_provenance_equal": True,
                            "final_input_matches_reference_centering": True})
    return results


if __name__ == "__main__":
    print(json.dumps(check_references(), indent=2))
