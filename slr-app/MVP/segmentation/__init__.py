"""Temporal segmentation and auto-trimming modules for VSL sign recognition."""

from .boundary_detector import (
    SegmentationConfig,
    compute_kinematic_signals,
    detect_single_sign_bounds,
    slice_feature_arrays,
    trim_single_sign,
)
from .sequence_splitter import (
    SequenceSplitConfig,
    build_multi_crop_bounds,
    hybrid_multi_crop_infer,
    make_slgcn_infer_fn,
    sliding_window_infer,
    split_sign_sequence,
)

__all__ = [
    "SegmentationConfig",
    "SequenceSplitConfig",
    "build_multi_crop_bounds",
    "compute_kinematic_signals",
    "detect_single_sign_bounds",
    "slice_feature_arrays",
    "trim_single_sign",
    "split_sign_sequence",
    "sliding_window_infer",
    "hybrid_multi_crop_infer",
    "make_slgcn_infer_fn",
]
