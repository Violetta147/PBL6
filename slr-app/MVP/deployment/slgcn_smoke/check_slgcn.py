"""SL-GCN CPU synthetic smoke test; not accuracy, parity or latency validation."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys

import numpy as np
import torch

from model.decouple_gcn_attn import Model


def main():
    root = Path(__file__).resolve().parent
    path = root / "gcnCkpt.pt"
    actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    expected_hash = "cd742dadd5b6d7aa1e4c742d618c78a9f616cfda7a6d5d968e14996f4f2e544f"
    if actual_hash != expected_hash:
        raise RuntimeError("Checkpoint SHA256 mismatch; stop and check file transfer.")

    torch.set_num_threads(2)
    # Audited checkpoint includes NumPy MT19937 RNG state saved with NumPy2.
    # Resolve only its specific NumPy globals to the installed NumPy1.26 classes.
    # Keep weights_only=True; no automatic fallback or restoring training RNG.
    allowed = [
        (np.core.multiarray._reconstruct, "numpy._core.multiarray._reconstruct"),
        np.ndarray, np.dtype, type(np.dtype(np.uint32)),
    ]
    with torch.serialization.safe_globals(allowed):
        unknown = torch.serialization.get_unsafe_globals_in_checkpoint(path)
        if unknown:
            raise RuntimeError(f"Unexpected checkpoint globals: {unknown}")
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    config = json.loads((root / "training_config.json").read_text(encoding="utf-8"))
    expected_args = dict(num_class=400, num_point=27, num_person=1, groups=16,
                         block_size=41, graph="graph.sign_27.Graph",
                         graph_args=dict(labeling_mode="spatial"), in_channels=2)
    if config["model_args"] != expected_args or checkpoint.get("model_args") != expected_args:
        raise RuntimeError("Unexpected model configuration.")
    if checkpoint.get("purpose") != "full_400_class_trainval_no_test":
        raise RuntimeError("Unexpected checkpoint purpose.")
    if checkpoint.get("epoch") != 52:
        raise RuntimeError("Unexpected checkpoint epoch.")

    model = Model(**expected_args)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    del checkpoint
    model.eval()
    if any(p.device.type != "cpu" for p in model.parameters()):
        raise RuntimeError("Model is not entirely on CPU.")
    if any(b.device.type != "cpu" for b in model.buffers()):
        raise RuntimeError("Model buffers are not entirely on CPU.")
    if model.graph.A.shape != (3, 27, 27):
        raise RuntimeError("Unexpected graph shape.")

    values = np.linspace(-1.0, 1.0, 2 * 150 * 27, dtype=np.float32).reshape(1, 2, 150, 27, 1)
    x = torch.from_numpy(values)
    with torch.inference_mode():
        logits = model(x, keep_prob=1.0)
    if tuple(logits.shape) != (1, 400):
        raise RuntimeError(f"Unexpected output shape: {tuple(logits.shape)}")
    if not bool(torch.isfinite(logits).all()):
        raise RuntimeError("Output contains NaN or Inf.")

    report = dict(test="SLGCN_CPU_synthetic_smoke", status="PASS",
                  utc=datetime.now(timezone.utc).isoformat(),
                  python=sys.version.split()[0], numpy=np.__version__, torch=torch.__version__,
                  checkpoint_sha256=actual_hash, strict_load=True,
                  model_args_match=True, checkpoint_epoch=52,
                  source_commit=config["official_commit"],
                  source_patch="Four tensor-construction device literals changed from cuda to cpu",
                  device=str(logits.device), input_shape=list(x.shape), output_shape=list(logits.shape),
                  finite_output=True, parameter_count=sum(p.numel() for p in model.parameters()),
                  limitations="Synthetic input only. No accuracy, CPU/GPU parity, camera or latency validation.")
    output = root / "slgcn_smoke_result.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Checkpoint SHA256: OK")
    print("Checkpoint config: OK")
    print("Strict load: OK")
    print("Device:", logits.device)
    print("Input shape:", tuple(x.shape))
    print("Output shape:", tuple(logits.shape))
    print("Finite output: True")
    print("PASS: SL-GCN CPU smoke test (synthetic input only)")
    print("Result saved:", output)


if __name__ == "__main__":
    main()
