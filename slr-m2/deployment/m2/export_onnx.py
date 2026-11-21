"""Export frozen SL-GCN 07b checkpoint to ONNX and verify numerical parity & speedup."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np
import torch
from torch import nn

from deployment.m1.common import DEFAULT_BUNDLE, ROOT
from deployment.m2.classifier import (
    deserialize_landmark_arrays,
    verify_bundle_utf8,
)

DEFAULT_SAMPLE_NPZ = ROOT / "outputs" / "sample_014159_landmarks.npz"


class _SLGCNOnnxWrapper(nn.Module):
    """Wraps frozen SLGCN with fixed 150-frame evaluation masks for clean static ONNX export."""

    def __init__(self, model: nn.Module, frames: int = 150) -> None:
        super().__init__()
        self.model = model
        self.register_buffer("real", torch.ones((1, frames), dtype=torch.bool))
        self.register_buffer("time", torch.zeros((1, frames, 2), dtype=torch.float32))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.model(x, self.real, self.time)


def _prepare_sample_input(bundle: Path, npz_path: Path) -> tuple[np.ndarray, int]:
    code_dir = str(bundle / "code")
    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)
    import slgcn_bone_07b as frozen

    arrays = deserialize_landmark_arrays(npz_path.read_bytes())
    source = object.__new__(frozen.BoneSequenceDataset)
    adapted = source.adapt_clip(arrays)

    class _SingleClip:
        def __len__(self) -> int:
            return 1

        def __getitem__(self, _index: int) -> dict[str, Any]:
            return {key: value.clone() for key, value in adapted.items()}

    window = frozen.BoneWindowDataset(_SingleClip(), training=False)[0]
    x = window["x"].unsqueeze(0).contiguous().numpy().astype(np.float32)
    return x, int(len(arrays["xy"]))


def export_slgcn_onnx(
    *,
    bundle: Path = DEFAULT_BUNDLE,
    out_path: Path | None = None,
    sample_npz: Path = DEFAULT_SAMPLE_NPZ,
    quantize_int8: bool = False,
    opset: int = 17,
    benchmark_runs: int = 20,
) -> dict[str, Any]:
    bundle = Path(bundle).resolve()
    identity = verify_bundle_utf8(bundle)
    raw_labels = identity.pop("labels")
    id_to_label = {int(v): str(k) for k, v in raw_labels.items()}

    code_dir = str(bundle / "code")
    if code_dir not in sys.path:
        sys.path.insert(0, code_dir)
    import architecture_models
    import slgcn_bone_07b as frozen

    model = architecture_models.build_model("sl_gcn", 400)
    checkpoint = torch.load(bundle / "best.pt", map_location="cpu", weights_only=False)
    model.load_state_dict(checkpoint["model"])
    model.float().eval()

    frames = int(frozen.CACHE_FRAMES)
    wrapper = _SLGCNOnnxWrapper(model, frames=frames).eval()
    target_path = Path(out_path).resolve() if out_path else (bundle / "slgcn_07b.onnx")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if sample_npz.is_file():
        sample_x, source_frames = _prepare_sample_input(bundle, sample_npz)
    else:
        rng = np.random.default_rng(42)
        sample_x = rng.normal(0.0, 0.25, size=(1, frames, 28, 8)).astype(np.float32)
        sample_x[:, :, 0, 4] = 1.0
        source_frames = frames

    dummy_torch = torch.from_numpy(sample_x)
    with torch.inference_mode():
        torch.onnx.export(
            wrapper,
            (dummy_torch,),
            str(target_path),
            input_names=["x"],
            output_names=["logits"],
            opset_version=int(opset),
            do_constant_folding=True,
            dynamo=False,
        )

    import onnx
    import onnxruntime as ort

    onnx_model = onnx.load(str(target_path))
    onnx.checker.check_model(onnx_model)

    sess_opts = ort.SessionOptions()
    sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess_opts.intra_op_num_threads = 4
    sess_opts.inter_op_num_threads = 1
    session = ort.InferenceSession(
        str(target_path),
        sess_options=sess_opts,
        providers=["CPUExecutionProvider"],
    )

    with torch.inference_mode():
        torch_logits = wrapper(dummy_torch).numpy()
    ort_logits = session.run(["logits"], {"x": sample_x})[0]

    max_abs_diff = float(np.max(np.abs(torch_logits - ort_logits)))
    if max_abs_diff >= 1e-4:
        raise AssertionError(f"ONNX parity diff too large: {max_abs_diff}")

    def _top5(logits_1d: np.ndarray) -> list[dict[str, Any]]:
        shifted = logits_1d - np.max(logits_1d)
        probs = np.exp(shifted)
        probs /= np.sum(probs)
        top_idx = np.argsort(-probs)[:5]
        return [
            {"label": id_to_label[int(i)], "label_id": int(i), "score": float(probs[i])}
            for i in top_idx
        ]

    torch_top5 = _top5(torch_logits[0])
    ort_top5 = _top5(ort_logits[0])
    if [item["label_id"] for item in torch_top5] != [item["label_id"] for item in ort_top5]:
        raise AssertionError(f"Top-5 label mismatch: torch={torch_top5} ort={ort_top5}")

    # Parity check on synthetic edge case input too
    rng = np.random.default_rng(7)
    rand_x = rng.normal(0.0, 0.3, size=(1, frames, 28, 8)).astype(np.float32)
    with torch.inference_mode():
        rand_torch = wrapper(torch.from_numpy(rand_x)).numpy()
    rand_ort = session.run(["logits"], {"x": rand_x})[0]
    rand_max_diff = float(np.max(np.abs(rand_torch - rand_ort)))
    if rand_max_diff >= 1e-4:
        raise AssertionError(f"Random input ONNX parity diff too large: {rand_max_diff}")

    # Warm timings
    for _ in range(3):
        with torch.inference_mode():
            wrapper(dummy_torch)
        session.run(["logits"], {"x": sample_x})

    torch_times: list[float] = []
    ort_times: list[float] = []
    for _ in range(max(1, benchmark_runs)):
        t0 = time.perf_counter()
        with torch.inference_mode():
            wrapper(dummy_torch)
        torch_times.append(time.perf_counter() - t0)

        t1 = time.perf_counter()
        session.run(["logits"], {"x": sample_x})
        ort_times.append(time.perf_counter() - t1)

    result: dict[str, Any] = {
        "onnx_path": str(target_path),
        "onnx_size_bytes": target_path.stat().st_size,
        "opset": int(opset),
        "source_frames": source_frames,
        "sample_max_abs_diff": max_abs_diff,
        "random_max_abs_diff": rand_max_diff,
        "torch_top1": torch_top5[0],
        "onnx_top1": ort_top5[0],
        "top5_exact_id_match": True,
        "torch_median_seconds": float(np.median(torch_times)),
        "onnx_median_seconds": float(np.median(ort_times)),
    }

    if quantize_int8:
        from onnxruntime.quantization import QuantType, quantize_dynamic

        int8_path = target_path.with_name(f"{target_path.stem}.int8.onnx")
        quantize_dynamic(
            str(target_path),
            str(int8_path),
            weight_type=QuantType.QUInt8,
        )
        int8_sess = ort.InferenceSession(
            str(int8_path),
            sess_options=sess_opts,
            providers=["CPUExecutionProvider"],
        )
        int8_logits = int8_sess.run(["logits"], {"x": sample_x})[0]
        int8_top5 = _top5(int8_logits[0])
        result["int8_path"] = str(int8_path)
        result["int8_size_bytes"] = int8_path.stat().st_size
        result["int8_top1"] = int8_top5[0]

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Export SL-GCN 07b best.pt to ONNX and verify parity")
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--sample-npz", type=Path, default=DEFAULT_SAMPLE_NPZ)
    parser.add_argument("--opset", type=int, default=17)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--quantize-int8", action="store_true")
    args = parser.parse_args()

    report = export_slgcn_onnx(
        bundle=args.bundle,
        out_path=args.out,
        sample_npz=args.sample_npz,
        quantize_int8=args.quantize_int8,
        opset=args.opset,
        benchmark_runs=args.runs,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
