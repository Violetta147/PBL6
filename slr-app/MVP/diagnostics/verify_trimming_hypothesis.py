"""Empirical verification of trimming hypothesis for SLR SL-GCN model.

Tests:
- Experiment A: Controlled synthetic ablation on ground truth clip 014159.mp4 (label: 'Dài', 59 frames)
- Experiment B: Real webcam clips untrimmed vs trimmed test
- Experiment C: Training dataset frame distribution analysis from index_qc.csv
"""

import csv
import json
import logging
from pathlib import Path
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verifier")

ROOT = Path(__file__).resolve().parents[1]
MVP_DIR = ROOT
DESKTOP_MVP = ROOT / "desktop_mvp"
LOCAL_DATA = ROOT / "local_data"
QC_CSV = ROOT / "deployment" / "slgcn_feature_trial" / "reference" / "training_qc" / "index_qc.csv"
OUTPUT_DIR = ROOT / "outputs" / "empirical_verification"

sys.path.insert(0, str(DESKTOP_MVP))
from check_clip import ClipRecognizer


def analyze_training_qc(qc_path: Path):
    """Experiment C: Analyze training frame distribution from index_qc.csv."""
    logger.info("Starting Experiment C: Training Dataset Analysis")
    rows = []
    with qc_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    lengths = np.array([int(r["frames_original"]) for r in rows])
    missing_before = np.array([float(r["missing_before_pct"]) for r in rows])
    missing_after = np.array([float(r["missing_after_pct"]) for r in rows])

    stats = {
        "count": int(len(lengths)),
        "min": int(np.min(lengths)),
        "max": int(np.max(lengths)),
        "mean": float(np.mean(lengths)),
        "std": float(np.std(lengths)),
        "median": float(np.median(lengths)),
        "q25": float(np.percentile(lengths, 25)),
        "q75": float(np.percentile(lengths, 75)),
        "iqr": float(np.percentile(lengths, 75) - np.percentile(lengths, 25)),
        "missing_before_mean": float(np.mean(missing_before)),
        "missing_after_mean": float(np.mean(missing_after)),
        "num_under_150": int(np.sum(lengths < 150)),
        "pct_under_150": float(100.0 * np.sum(lengths < 150) / len(lengths)),
        "cycles_min": float(150.0 / np.max(lengths)),
        "cycles_max": float(150.0 / np.min(lengths)),
        "cycles_mean": float(np.mean(150.0 / lengths)),
        "cycles_median": float(np.median(150.0 / lengths)),
    }
    return stats, lengths


def pad_arrays_static(arrs: dict, n_pre: int, n_post: int) -> dict:
    """Pad arrays by holding the first and last frame."""
    T = len(arrs["upper_body"])
    T_new = T + n_pre + n_post
    new_arrs = {}
    for k, v in arrs.items():
        if k in ("frame_indices", "timestamps"):
            continue
        pre = np.repeat(v[:1], n_pre, axis=0) if n_pre > 0 else np.empty((0,) + v.shape[1:], dtype=v.dtype)
        post = np.repeat(v[-1:], n_post, axis=0) if n_post > 0 else np.empty((0,) + v.shape[1:], dtype=v.dtype)
        new_arrs[k] = np.concatenate([pre, v, post], axis=0)
    new_arrs["frame_indices"] = np.arange(T_new, dtype=np.int64)
    new_arrs["timestamps"] = np.arange(T_new, dtype=np.float64) / 30.0
    return new_arrs


def pad_arrays_with_idle(arrs: dict, idle_arrs: dict, n_pre: int, n_post: int) -> dict:
    """Pad arrays using genuine resting frames from a webcam clip."""
    T = len(arrs["upper_body"])
    T_new = T + n_pre + n_post
    new_arrs = {}
    for k, v in arrs.items():
        if k in ("frame_indices", "timestamps"):
            continue
        idle_v = idle_arrs[k]
        if n_pre > 0:
            if n_pre <= len(idle_v):
                pre = idle_v[:n_pre]
            else:
                repeats = (n_pre // len(idle_v)) + 1
                pre = np.tile(idle_v, (repeats,) + (1,) * (idle_v.ndim - 1))[:n_pre]
        else:
            pre = np.empty((0,) + v.shape[1:], dtype=v.dtype)

        if n_post > 0:
            if n_post <= len(idle_v):
                post = idle_v[-n_post:]
            else:
                repeats = (n_post // len(idle_v)) + 1
                post = np.tile(idle_v, (repeats,) + (1,) * (idle_v.ndim - 1))[:n_post]
        else:
            post = np.empty((0,) + v.shape[1:], dtype=v.dtype)

        new_arrs[k] = np.concatenate([pre, v, post], axis=0)
    new_arrs["frame_indices"] = np.arange(T_new, dtype=np.int64)
    new_arrs["timestamps"] = np.arange(T_new, dtype=np.float64) / 30.0
    return new_arrs


def run_experiment_a(recognizer: ClipRecognizer, gt_path: Path, idle_path: Path):
    """Experiment A: Synthetic / Controlled padding on 014159.mp4."""
    logger.info("Starting Experiment A: Synthetic Ablation on 014159.mp4")

    gt_res = recognizer.extract_video(gt_path, recognizer.config)
    gt_arrays = gt_res.arrays
    dai_idx = recognizer.labels["gloss_to_idx"]["Dài"]

    # Extract idle frames from a webcam recording
    idle_res = recognizer.extract_video(idle_path, recognizer.config)
    idle_arrays = idle_res.arrays

    pad_levels = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45]

    results_static = []
    results_idle = []

    logger.info("Running Sub-test A1: Static Hold Padding...")
    for pad in pad_levels:
        padded = pad_arrays_static(gt_arrays, pad, pad)
        T_pad = len(padded["upper_body"])
        tensor, quality = recognizer.prepare_arrays(padded)
        with torch.inference_mode():
            logits = recognizer.model(torch.from_numpy(tensor), keep_prob=1.0)
        probs = logits.softmax(dim=1)[0].numpy()
        dai_prob = float(probs[dai_idx])
        dai_rank = int((probs > dai_prob).sum()) + 1
        top1_idx = int(probs.argmax())
        top1_gloss = recognizer.labels["idx_to_gloss"][str(top1_idx)]
        top1_prob = float(probs[top1_idx])
        entropy = -float(np.sum(probs * np.log2(probs + 1e-12)))

        row = {
            "pad": pad,
            "total_frames": T_pad,
            "effective_cycles": round(150.0 / T_pad, 2),
            "top1_gloss": top1_gloss,
            "top1_prob": round(top1_prob, 5),
            "dai_prob": round(dai_prob, 5),
            "dai_rank": dai_rank,
            "entropy": round(entropy, 4),
            "missing_after_pct": round(float(quality["missing_after_pct"]), 2),
        }
        results_static.append(row)

    logger.info("Running Sub-test A2: Real Resting/Idle Posture Padding...")
    for pad in pad_levels:
        padded = pad_arrays_with_idle(gt_arrays, idle_arrays, pad, pad)
        T_pad = len(padded["upper_body"])
        tensor, quality = recognizer.prepare_arrays(padded)
        with torch.inference_mode():
            logits = recognizer.model(torch.from_numpy(tensor), keep_prob=1.0)
        probs = logits.softmax(dim=1)[0].numpy()
        dai_prob = float(probs[dai_idx])
        dai_rank = int((probs > dai_prob).sum()) + 1
        top1_idx = int(probs.argmax())
        top1_gloss = recognizer.labels["idx_to_gloss"][str(top1_idx)]
        top1_prob = float(probs[top1_idx])
        entropy = -float(np.sum(probs * np.log2(probs + 1e-12)))

        row = {
            "pad": pad,
            "total_frames": T_pad,
            "effective_cycles": round(150.0 / T_pad, 2),
            "top1_gloss": top1_gloss,
            "top1_prob": round(top1_prob, 5),
            "dai_prob": round(dai_prob, 5),
            "dai_rank": dai_rank,
            "entropy": round(entropy, 4),
            "missing_after_pct": round(float(quality["missing_after_pct"]), 2),
        }
        results_idle.append(row)

    return results_static, results_idle


def detect_active_segment_v2(arrays: dict) -> tuple[int, int]:
    """Detect active sign window based on wrist motion, elevation, and hand presence."""
    ub = arrays["upper_body"]  # (T, 7, 2)
    T = len(ub)
    det = arrays["detection_masks"]  # (T, 4): [pose, face, left, right]

    # Hand detection mask (at least one hand detected)
    has_hand = (det[:, 2] == 1) | (det[:, 3] == 1)

    # Wrists are index 5 (left wrist) and index 6 (right wrist)
    lw = ub[:, 5]
    rw = ub[:, 6]

    # Motion speed (displacement between consecutive frames)
    diff_l = np.linalg.norm(np.diff(lw, axis=0), axis=-1)
    diff_r = np.linalg.norm(np.diff(rw, axis=0), axis=-1)
    speed = np.maximum(np.nan_to_num(diff_l), np.nan_to_num(diff_r))
    speed = np.pad(speed, (0, 1), mode="edge")

    # In body coordinates, shoulder is y ≈ 0. Wrists above waist/hips have y < 1.0
    wrist_y = np.minimum(lw[:, 1], rw[:, 1])
    is_elevated = wrist_y < 1.0

    # Frame is active if hands are present and either moving or elevated
    active_mask = has_hand & (is_elevated | (speed > 0.02))

    active_indices = np.where(active_mask)[0]
    if len(active_indices) < 10:
        # Fallback: find frames with highest wrist speed
        thresh = np.percentile(speed, 50)
        active_indices = np.where(speed > thresh)[0]

    if len(active_indices) == 0:
        # Ultimate fallback: middle 55 frames
        mid = T // 2
        return max(0, mid - 28), min(T, mid + 28)

    start = int(active_indices[0])
    end = int(active_indices[-1]) + 1

    # Include small margin of 4 frames around activity
    start = max(0, start - 4)
    end = min(T, end + 4)

    # If the window is too long (> 85 frames), trim the tails where speed is lowest
    if (end - start) > 85:
        # Find peak motion center
        center = start + int(np.argmax(speed[start:end]))
        start = max(0, center - 30)
        end = min(T, center + 30)

    # Enforce minimum sign duration matching VSL400 (~45-60 frames)
    if (end - start) < 45:
        needed = 45 - (end - start)
        pad_l = needed // 2
        pad_r = needed - pad_l
        start = max(0, start - pad_l)
        end = min(T, end + pad_r)

    return start, end


def slice_arrays(arrays: dict, start: int, end: int) -> dict:
    """Slice arrays dictionary to [start, end]."""
    new_arrs = {}
    T_new = end - start
    for k, v in arrays.items():
        if k in ("frame_indices", "timestamps"):
            continue
        new_arrs[k] = v[start:end].copy()
    new_arrs["frame_indices"] = np.arange(T_new, dtype=np.int64)
    new_arrs["timestamps"] = np.arange(T_new, dtype=np.float64) / 30.0
    return new_arrs


def run_experiment_b(recognizer: ClipRecognizer, data_dir: Path):
    """Experiment B: Compare Untrimmed vs Active-Trimmed on real webcam clips."""
    logger.info("Starting Experiment B: Real Webcam Clips Evaluation")

    clips = sorted(data_dir.glob("webcam_*.avi"))
    # Screen long clips (T >= 85 frames)
    long_clips = []
    for c in clips:
        if c.stat().st_size < 10000:
            continue
        try:
            cap = recognizer.extract_video(c, recognizer.config)
            if cap.status in ("success", "success_with_warning") and cap.decoded_frames >= 85:
                long_clips.append((c, cap))
        except Exception as err:
            logger.warning(f"Failed to extract {c.name}: {err}")

    logger.info(f"Screened {len(long_clips)} candidate long webcam clips.")

    results = []

    for path, cap_res in long_clips:
        arrays_full = cap_res.arrays
        T_full = len(arrays_full["upper_body"])

        # Attempt untrimmed prepare_arrays
        try:
            tensor_full, quality_full = recognizer.prepare_arrays(arrays_full)
        except ValueError as err:
            logger.warning(f"Clip {path.name} cannot be recognized in untrimmed mode: {err}")
            continue

        with torch.inference_mode():
            logits_full = recognizer.model(torch.from_numpy(tensor_full), keep_prob=1.0)
        probs_full = logits_full.softmax(dim=1)[0].numpy()
        top1_idx_full = int(probs_full.argmax())
        top1_gloss_full = recognizer.labels["idx_to_gloss"][str(top1_idx_full)]
        top1_prob_full = float(probs_full[top1_idx_full])
        entropy_full = -float(np.sum(probs_full * np.log2(probs_full + 1e-12)))

        # Active boundary detection & trimming
        start_idx, end_idx = detect_active_segment_v2(arrays_full)
        arrays_trim = slice_arrays(arrays_full, start_idx, end_idx)
        T_trim = len(arrays_trim["upper_body"])

        try:
            tensor_trim, quality_trim = recognizer.prepare_arrays(arrays_trim)
        except ValueError as err:
            logger.warning(f"Trimmed clip {path.name} failed: {err}")
            continue

        with torch.inference_mode():
            logits_trim = recognizer.model(torch.from_numpy(tensor_trim), keep_prob=1.0)
        probs_trim = logits_trim.softmax(dim=1)[0].numpy()
        top1_idx_trim = int(probs_trim.argmax())
        top1_gloss_trim = recognizer.labels["idx_to_gloss"][str(top1_idx_trim)]
        top1_prob_trim = float(probs_trim[top1_idx_trim])
        entropy_trim = -float(np.sum(probs_trim * np.log2(probs_trim + 1e-12)))

        # Top 2 margin
        sorted_full = np.sort(probs_full)[::-1]
        margin_full = float(sorted_full[0] - sorted_full[1])
        sorted_trim = np.sort(probs_trim)[::-1]
        margin_trim = float(sorted_trim[0] - sorted_trim[1])

        item = {
            "clip": path.name,
            "untrimmed": {
                "frames": T_full,
                "top1_gloss": top1_gloss_full,
                "top1_prob": round(top1_prob_full, 5),
                "entropy": round(entropy_full, 4),
                "margin_top2": round(margin_full, 5),
                "missing_after_pct": round(float(quality_full["missing_after_pct"]), 2),
            },
            "trimmed": {
                "active_window": [start_idx, end_idx],
                "frames": T_trim,
                "top1_gloss": top1_gloss_trim,
                "top1_prob": round(top1_prob_trim, 5),
                "entropy": round(entropy_trim, 4),
                "margin_top2": round(margin_trim, 5),
                "missing_after_pct": round(float(quality_trim["missing_after_pct"]), 2),
            },
            "diff_confidence": round(float(top1_prob_trim - top1_prob_full), 5),
            "diff_entropy": round(float(entropy_trim - entropy_full), 4),
            "gloss_changed": bool(top1_gloss_full != top1_gloss_trim),
        }
        results.append(item)
        logger.info(f"Processed {path.name}: T {T_full} -> {T_trim}, Conf {top1_prob_full*100:.1f}% -> {top1_prob_trim*100:.1f}%")

    return results


def generate_visualizations(stats_c, lengths_c, exp_a_static, exp_a_idle, exp_b, output_dir: Path):
    """Generate high-resolution figures for report visualization."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Figure 1: Synthetic Ablation on 014159.mp4
    fig, axes = plt.subplots(3, 1, figsize=(10, 11), sharex=True)
    frames_static = [r["total_frames"] for r in exp_a_static]
    dai_prob_static = [r["dai_prob"] * 100 for r in exp_a_static]
    dai_rank_static = [r["dai_rank"] for r in exp_a_static]
    entropy_static = [r["entropy"] for r in exp_a_static]

    frames_idle = [r["total_frames"] for r in exp_a_idle]
    dai_prob_idle = [r["dai_prob"] * 100 for r in exp_a_idle]
    dai_rank_idle = [r["dai_rank"] for r in exp_a_idle]
    entropy_idle = [r["entropy"] for r in exp_a_idle]

    # Panel 1: Softmax confidence of "Dài"
    axes[0].plot(frames_static, dai_prob_static, "o-", color="#1f77b4", linewidth=2.5, markersize=8, label="Static Boundary Padding (P1)")
    axes[0].plot(frames_idle, dai_prob_idle, "s--", color="#d62728", linewidth=2.5, markersize=8, label="Webcam Resting Idle Padding (P2)")
    axes[0].axvline(59, color="gray", linestyle=":", label="Original GT length (59 frames)")
    axes[0].axvline(119, color="purple", linestyle="--", label="Webcam 4.0s length (~119 frames)")
    axes[0].set_ylabel("Softmax Conf (%)", fontsize=11, fontweight="bold")
    axes[0].set_title("Experiment A: Impact of Idle Padding on Ground Truth Clip 'Dài' (014159.mp4)", fontsize=13, fontweight="bold")
    axes[0].grid(True, linestyle="--", alpha=0.6)
    axes[0].legend(loc="lower left", frameon=True)
    axes[0].set_ylim(-2, 105)

    # Panel 2: Rank of "Dài"
    axes[1].plot(frames_static, dai_rank_static, "o-", color="#1f77b4", linewidth=2.5, markersize=8, label="Static Boundary Padding")
    axes[1].plot(frames_idle, dai_rank_idle, "s--", color="#d62728", linewidth=2.5, markersize=8, label="Webcam Resting Idle Padding")
    axes[1].axvline(59, color="gray", linestyle=":")
    axes[1].axvline(119, color="purple", linestyle="--")
    axes[1].set_ylabel("Rank of 'Dài'", fontsize=11, fontweight="bold")
    axes[1].set_title("Rank Stability as Sequence Length Expands (1 = Top-1)", fontsize=12, fontweight="bold")
    axes[1].grid(True, linestyle="--", alpha=0.6)
    axes[1].set_ylim(0.5, 3.5)
    axes[1].invert_yaxis()

    # Panel 3: Softmax Entropy
    axes[2].plot(frames_static, entropy_static, "o-", color="#1f77b4", linewidth=2.5, markersize=8, label="Static Boundary Padding")
    axes[2].plot(frames_idle, entropy_idle, "s--", color="#d62728", linewidth=2.5, markersize=8, label="Webcam Resting Idle Padding")
    axes[2].axvline(59, color="gray", linestyle=":")
    axes[2].axvline(119, color="purple", linestyle="--")
    axes[2].set_ylabel("Entropy (bits)", fontsize=11, fontweight="bold")
    axes[2].set_xlabel("Total Clip Length T (frames)", fontsize=11, fontweight="bold")
    axes[2].set_title("Softmax Uncertainty (Shannon Entropy) with Sequence Dilution", fontsize=12, fontweight="bold")
    axes[2].grid(True, linestyle="--", alpha=0.6)

    fig.tight_layout()
    fig1_path = output_dir / "fig1_synthetic_ablation.png"
    fig.savefig(fig1_path, dpi=200)
    plt.close(fig)

    # 2. Figure 2: Training QC Distribution
    fig, (ax_hist, ax_box) = plt.subplots(2, 1, figsize=(9, 7), gridspec_kw={"height_ratios": [3, 1]}, sharex=True)
    ax_hist.hist(lengths_c, bins=15, color="#2ca02c", edgecolor="black", alpha=0.75, rwidth=0.85)
    ax_hist.axvline(stats_c["mean"], color="red", linestyle="--", linewidth=2, label=f"Mean: {stats_c['mean']:.1f} frames")
    ax_hist.axvline(stats_c["median"], color="blue", linestyle="-.", linewidth=2, label=f"Median: {stats_c['median']:.1f} frames")
    ax_hist.axvline(119, color="purple", linestyle=":", linewidth=2, label="Webcam 4.0s (~119 frames)")
    ax_hist.set_ylabel("Sample Count", fontsize=11, fontweight="bold")
    ax_hist.set_title(f"Experiment C: VSL400 Training Dataset Frame Length Distribution (N={stats_c['count']})", fontsize=13, fontweight="bold")
    ax_hist.legend(loc="upper right", frameon=True)
    ax_hist.grid(True, linestyle="--", alpha=0.5)

    ax_box.boxplot(lengths_c, vert=False, patch_artist=True,
                   boxprops=dict(facecolor="#2ca02c", alpha=0.5),
                   medianprops=dict(color="blue", linewidth=2))
    ax_box.set_xlabel("Original Video Frames (T)", fontsize=11, fontweight="bold")
    ax_box.set_yticks([])
    ax_box.grid(True, linestyle="--", alpha=0.5)

    fig.tight_layout()
    fig2_path = output_dir / "fig2_training_distribution.png"
    fig.savefig(fig2_path, dpi=200)
    plt.close(fig)

    # 3. Figure 3: Real Webcam Untrimmed vs Trimmed Comparison
    if exp_b:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        indices = np.arange(len(exp_b))
        names = [f"Clip {i+1}\n({r['trimmed']['frames']}f)" for i, r in enumerate(exp_b)]
        untrim_confs = [r["untrimmed"]["top1_prob"] * 100 for r in exp_b]
        trim_confs = [r["trimmed"]["top1_prob"] * 100 for r in exp_b]

        untrim_ent = [r["untrimmed"]["entropy"] for r in exp_b]
        trim_ent = [r["trimmed"]["entropy"] for r in exp_b]

        width = 0.35
        ax1.bar(indices - width/2, untrim_confs, width, label="Untrimmed (~4s, ~119f)", color="#d62728", alpha=0.85)
        ax1.bar(indices + width/2, trim_confs, width, label="Trimmed (Active Sign)", color="#2ca02c", alpha=0.85)
        ax1.set_ylabel("Top-1 Confidence (%)", fontsize=11, fontweight="bold")
        ax1.set_title("Top-1 Softmax Confidence Comparison", fontsize=12, fontweight="bold")
        ax1.set_xticks(indices)
        ax1.set_xticklabels(names)
        ax1.grid(True, linestyle="--", alpha=0.5)
        ax1.legend(loc="upper left")

        ax2.bar(indices - width/2, untrim_ent, width, label="Untrimmed (~4s, ~119f)", color="#d62728", alpha=0.85)
        ax2.bar(indices + width/2, trim_ent, width, label="Trimmed (Active Sign)", color="#2ca02c", alpha=0.85)
        ax2.set_ylabel("Entropy (bits)", fontsize=11, fontweight="bold")
        ax2.set_title("Softmax Uncertainty (Entropy)", fontsize=12, fontweight="bold")
        ax2.set_xticks(indices)
        ax2.set_xticklabels(names)
        ax2.grid(True, linestyle="--", alpha=0.5)
        ax2.legend(loc="upper right")

        fig.tight_layout()
        fig3_path = output_dir / "fig3_webcam_untrimmed_vs_trimmed.png"
        fig.savefig(fig3_path, dpi=200)
        plt.close(fig)


def main():
    start_time = time.perf_counter()
    recognizer = ClipRecognizer()

    # Exp C
    stats_c, lengths_c = analyze_training_qc(QC_CSV)

    # Exp A
    gt_path = LOCAL_DATA / "014159.mp4"
    idle_path = LOCAL_DATA / "webcam_20261115_082705_985281.avi"
    exp_a_static, exp_a_idle = run_experiment_a(recognizer, gt_path, idle_path)

    # Exp B
    exp_b = run_experiment_b(recognizer, LOCAL_DATA)

    # Visualizations
    generate_visualizations(stats_c, lengths_c, exp_a_static, exp_a_idle, exp_b, OUTPUT_DIR)

    # Save summary report JSON
    summary_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": round(time.perf_counter() - start_time, 2),
        "experiment_c_training_qc": stats_c,
        "experiment_a_static_hold": exp_a_static,
        "experiment_a_idle_padding": exp_a_idle,
        "experiment_b_webcam_clips": exp_b,
    }
    summary_path = OUTPUT_DIR / "verification_results.json"
    summary_path.write_text(json.dumps(summary_report, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Verification complete in {summary_report['elapsed_seconds']}s.")
    logger.info(f"Saved results to {summary_path}")


if __name__ == "__main__":
    main()
