# SL-GCN CPU synthetic smoke test

Copy this folder to ~/pbl6_edge_islr/ and run check_slgcn.py with ~/pbl6_edge_islr/.venv/bin/python. Requires the already confirmed NumPy1.26.4 and PyTorch2.11.0+cpu. No new libraries are proposed for this test.

Source: https://github.com/jackyjsy/CVPR21Chal-SLR/tree/de6c53a6fbbc08a5d9a728e33614a4541836714c/SL-GCN . All seven original source file hashes were verified against the project's saved training config before patching. Only four device='cuda' literals in model/decouple_gcn_attn.py were changed to device='cpu'; an AST comparison checked that this was the only semantic source difference. Parameter names and tensor shapes are unchanged, but CPU/GPU logit parity still requires separate verification.

The checkpoint is the previously audited trainval_v3_seed42_60ep_v1 best.pt, epoch52, copied as gcnCkpt.pt. It contains model_state_dict and training metadata/RNG; the script checks its SHA256, keeps weights_only=True and allowlists only the specific NumPy reconstruct/ndarray/dtype/UInt32DType definitions required for this NumPy2 RNG representation on NumPy1.26. The training RNG and optimizer state are not restored. No unrestricted load fallback is used. Reference: https://docs.pytorch.org/docs/2.11/notes/serialization.html#torch-load-with-weights-only-true .

Evaluation mode and keep_prob=1.0 disable training DropBlock. The input (1,2,150,27,1) is synthetic, not processed camera landmarks. Success requires strict load, CPU parameters/buffers and finite output (1,400), then writes slgcn_smoke_result.json. This does not validate recognition accuracy, preprocessing, CPU/GPU parity, latency or webcam end-to-end behavior.

Original source prints Attention Enabled! ten times and uses older initialization APIs that can emit warnings. Preserve all output; runtime on Pi is pending. Local checks cover source provenance, the four-literal patch, syntax and checkpoint hash, not a local PyTorch forward.

Checkpoint naming cross-check (2026-10-29): the user's checkpoints folder 1fc1N1eTl74Q_Zu04VXI70C4uqIOgAhJi contains best_epoch_052.pt (159txU7iwqiZgV5foFPNke10EjVBoKCBF), size35,414,971. Its latest.json points to that filename and declares best_sha256 cd742dadd5b6d7aa1e4c742d618c78a9f616cfda7a6d5d968e14996f4f2e544f, matching this package's actual hash and the saved test metrics. Initial download was named best.pt in the full-run folder; this cross-check establishes the named snapshot's manifest hash matches the packaged checkpoint. No new checkpoint was substituted.
