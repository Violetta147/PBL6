"""Run the frozen SL-GCN pipeline on one labeled video on CPU."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "deployment/feature_extract"
ADAPTER = ROOT / "deployment/slgcn_feature_trial"
MODEL = ROOT / "deployment/slgcn_smoke"
LABELS = ROOT / "deployment/handoff_assets/label_map_v1.json"
LABEL_SHA = "5f00478c30b45fc26842bbb22852253f79cc7f4bf333f780436a699934c26344"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path, expected):
    actual = digest(path)
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch: {path}")
    return actual


def load_model(torch, np, model_type):
    torch.set_num_threads(2)
    core = np._core if hasattr(np, "_core") else np.core
    rebuild = core.multiarray._reconstruct
    allowed = [
        (rebuild, "numpy._core.multiarray._reconstruct"),
        (rebuild, "numpy.core.multiarray._reconstruct"),
        np.ndarray, np.dtype, type(np.dtype(np.uint32)),
    ]
    checkpoint_path = MODEL / "gcnCkpt.pt"
    with torch.serialization.safe_globals(allowed):
        unknown = torch.serialization.get_unsafe_globals_in_checkpoint(checkpoint_path)
        if unknown:
            raise ValueError(f"Unexpected checkpoint globals: {unknown}")
        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    config = read_json(MODEL / "training_config.json")
    args = config["model_args"]
    if (checkpoint.get("model_args") != args or checkpoint.get("epoch") != 52
            or checkpoint.get("purpose") != "full_400_class_trainval_no_test"):
        raise ValueError("Unexpected checkpoint configuration.")
    model = model_type(**args)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    return model.eval()


class ClipRecognizer:
    """Load and validate the frozen pipeline once, then recognize clips on CPU."""

    def __init__(self):
        start = time.perf_counter()
        sys.dont_write_bytecode = True
        for directory in (EXTRACT, ADAPTER, MODEL):
            sys.path.insert(0, str(directory))
        import cv2
        import mediapipe
        import numpy as np
        import torch
        from model.decouple_gcn_attn import Model
        from prepare_clip import prepare_arrays, verify_bundle
        from src.extraction.mediapipe_extractor import extract_video
        from verify_reference import check_references

        self.imports_seconds = time.perf_counter() - start
        phase = time.perf_counter()
        for name, expected in read_json(EXTRACT / "manifest.json")["sha256"].items():
            verify(EXTRACT / name, expected)
        model_manifest = read_json(MODEL / "manifest.json")["files"]
        for name, item in model_manifest.items():
            if name.endswith((".py", ".pt", ".json")) and name != "check_slgcn.py":
                verify(MODEL / name, item["sha256"])
        verify(LABELS, LABEL_SHA)
        verify_bundle()
        self.references = check_references()
        self.labels = read_json(LABELS)
        self.config = read_json(EXTRACT / "extraction_config.json")
        self.verification_seconds = time.perf_counter() - phase

        phase = time.perf_counter()
        self.model = load_model(torch, np, Model)
        self.model_load_seconds = time.perf_counter() - phase
        self.torch = torch
        self.extract_video = extract_video
        self.prepare_arrays = prepare_arrays
        self.checkpoint_sha = model_manifest["gcnCkpt.pt"]["sha256"]
        self.versions = {
            "python": sys.version.split()[0], "opencv": cv2.__version__,
            "mediapipe": mediapipe.__version__, "numpy": np.__version__,
            "torch": torch.__version__,
        }

    def recognize(self, video, expected=None, expected_frames=None):
        start = time.perf_counter()
        video_sha = digest(video)
        expected_id = self.labels["gloss_to_idx"].get(expected)
        if expected is not None and expected_id is None:
            raise ValueError(f"Unknown expected label: {expected}")

        phase = time.perf_counter()
        result = self.extract_video(video, self.config)
        extraction_seconds = time.perf_counter() - phase
        if result.error or result.status not in ("success", "success_with_warning"):
            raise RuntimeError(result.error or f"Extractor status: {result.status}")
        if expected_frames is not None and result.decoded_frames != expected_frames:
            raise ValueError(f"Expected {expected_frames} frames, decoded {result.decoded_frames}.")

        phase = time.perf_counter()
        tensor, quality = self.prepare_arrays(result.arrays)
        adapter_seconds = time.perf_counter() - phase
        if quality["missing_after_pct"] >= 100:
            raise ValueError("No usable landmarks in this clip.")

        phase = time.perf_counter()
        with self.torch.inference_mode():
            logits = self.model(self.torch.from_numpy(tensor), keep_prob=1.0)
        forward_seconds = time.perf_counter() - phase
        if logits.shape != (1, 400) or not bool(self.torch.isfinite(logits).all()):
            raise RuntimeError("Unexpected classifier output.")
        scores, indexes = logits.softmax(dim=1)[0].topk(5)
        top5 = [
            {"index": i, "gloss": self.labels["idx_to_gloss"][str(i)], "softmax": score}
            for i, score in zip(indexes.tolist(), scores.tolist())
        ]
        return {
            "video": str(video.resolve()),
            "video_sha256": video_sha,
            "expected_gloss": expected,
            "decoded_frames": result.decoded_frames,
            "top1_correct": None if expected_id is None else top5[0]["index"] == expected_id,
            "top5": top5,
            "reference_checks": self.references,
            "geometry_blocked_source_frames": int(quality["geometry_blocked"][:result.decoded_frames].sum()),
            "missing_after_pct": quality["missing_after_pct"],
            "checkpoint_sha256": self.checkpoint_sha,
            "label_map_sha256": LABEL_SHA,
            "versions": self.versions,
            "seconds": {"extraction": extraction_seconds, "adapter": adapter_seconds,
                        "forward_first": forward_seconds,
                        "clip_total": time.perf_counter() - start},
        }


def save_report(report, directory):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    destination = ROOT / "outputs" / directory / stamp / "report.json"
    destination.parent.mkdir(parents=True, exist_ok=False)
    output = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    destination.write_text(output + "\n", encoding="utf-8")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--expected", required=True, help="Gloss from source metadata")
    parser.add_argument("--expected-frames", type=int, help="Frame count from source metadata")
    args = parser.parse_args()
    start = time.perf_counter()
    recognizer = ClipRecognizer()
    report = recognizer.recognize(args.video, args.expected, args.expected_frames)
    report["seconds"].update(
        imports=recognizer.imports_seconds, verification=recognizer.verification_seconds,
        model_load=recognizer.model_load_seconds, total_before_report_write=time.perf_counter() - start,
    )
    destination = save_report(report, "desktop_clip_checks")
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    print("Report:", destination)


if __name__ == "__main__":
    main()
