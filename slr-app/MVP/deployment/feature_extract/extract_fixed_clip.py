"""Export the audited baseline extractor's per-frame features, without classification."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import csv
import hashlib
import json
import time

import numpy as np


def main():
    root=Path(__file__).resolve().parent
    manifest=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    for name,expected in manifest["sha256"].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:
            raise RuntimeError(f"Source/config SHA256 mismatch: {name}")
    folder=root.parent/"camera_landmarks/inputs/20261029T033837_152428Z"
    video=folder/"camera_test.avi"
    digest=hashlib.sha256(video.read_bytes()).hexdigest()
    if digest!="2d0b0ffc40e1437741fd26544b4d9f879ad6570764b01a4dabdea2584073000a":
        raise RuntimeError("Unexpected fixed input video.")
    with (folder/"frame_times.csv").open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    capture_times=np.array([float(r["read_complete_seconds_since_start"]) for r in rows],dtype=np.float64)
    if len(rows)!=121 or [int(r["frame_index_0based"]) for r in rows]!=list(range(121)) or not np.all(np.diff(capture_times)>0):
        raise RuntimeError("Unexpected frame timestamp CSV.")
    cfg=json.loads((root/"extraction_config.json").read_text(encoding="utf-8"))
    from src.extraction.mediapipe_extractor import extract_video
    print("Source/config/input checks: OK",flush=True)
    print("Extracting all121 frames with original Pose1/Hands1 source, face processing off.",flush=True)
    print("This includes anatomical hand assignment and hand/body normalization; please wait.",flush=True)
    started=time.perf_counter()
    result=extract_video(video,cfg)
    elapsed=time.perf_counter()-started
    if result.status=="failed" or result.error:
        raise RuntimeError(result.error or "Extractor failed.")
    if result.decoded_frames!=121:
        raise RuntimeError(f"Unexpected extracted frame count: {result.decoded_frames}")
    expected=dict(left_hand_local=(121,21,2),right_hand_local=(121,21,2),
                  upper_body=(121,7,2),left_palm_body=(121,5,2),right_palm_body=(121,5,2),
                  left_hand_body_relations=(121,2),right_hand_body_relations=(121,2),
                  hand_scales=(121,2),detection_masks=(121,4),handedness_valid=(121,2),
                  frame_indices=(121,),timestamps=(121,))
    if set(result.arrays)!=set(expected):
        raise RuntimeError(f"Unexpected feature keys: {list(result.arrays)}")
    stats={}
    for name,shape in expected.items():
        a=result.arrays[name]
        if tuple(a.shape)!=shape or a.dtype.hasobject:
            raise RuntimeError(f"Invalid array {name}: {a.shape}, {a.dtype}")
        if np.isinf(a).any():
            raise RuntimeError(f"Inf values in {name}")
        stats[name]=dict(shape=list(a.shape),dtype=str(a.dtype),nan_count=int(np.isnan(a).sum()))
    if not np.array_equal(result.arrays["frame_indices"],np.arange(121)):
        raise RuntimeError("Extractor frame order differs from CSV.")
    masks=result.arrays["detection_masks"]
    valid=result.arrays["handedness_valid"]
    # Preserve source video-header-based timestamps; store actual capture times separately.
    out=root/"results"/datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    out.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(out/"features_raw.npz",**result.arrays)
    np.save(out/"capture_read_complete_seconds.npy",capture_times,allow_pickle=False)
    reloaded=np.load(out/"features_raw.npz",allow_pickle=False)
    with reloaded:
        for name,a in result.arrays.items():
            if not np.array_equal(reloaded[name],a,equal_nan=True):
                raise RuntimeError(f"NPZ round-trip mismatch: {name}")
    metadata=dict(status=result.status,source_metadata=result.metadata,
                  source_warnings=result.warnings,video_sha256=digest,
                  elapsed_extraction_seconds=elapsed,decoded_frames=result.decoded_frames,
                  shapes_and_missing=stats,
                  pose_detected_pct=float(masks[:,0].mean()*100),
                  anatomical_left_assigned_pct=float(masks[:,2].mean()*100),
                  anatomical_right_assigned_pct=float(masks[:,3].mean()*100),
                  both_hands_assigned_pct=float(np.logical_and(masks[:,2],masks[:,3]).mean()*100),
                  both_hands_confident_pct=float(np.all(valid,axis=1).mean()*100),
                  assignment_methods=ast.literal_eval(result.metadata["assignment_methods"]),
                  timestamps_note="features_raw timestamps are unchanged source index/AVI nominal30FPS. capture_read_complete_seconds.npy separately preserves real approximately15FPS capture times. These are not sensor exposure times.",
                  limitations="Per-frame feature export only. NaN preserved. No temporal repair/resampling, final128D/model tensor adapter, classifier, reference parity or accuracy check. Not a frozen dataset/training-cache replacement.")
    (out/"metadata.json").write_text(json.dumps(metadata,indent=2)+"\n",encoding="utf-8")
    (out/"effective_config.json").write_text(json.dumps(cfg,indent=2)+"\n",encoding="utf-8")
    (root/"latest_result.json").write_text(json.dumps(dict(output_dir=str(out),video_sha256=digest),indent=2)+"\n",encoding="utf-8")
    print("Feature export: OK | frames=121 | NPZ round-trip=OK")
    print(f"Both hands assigned: {metadata['both_hands_assigned_pct']:.1f}%")
    print(f"Both hands confident: {metadata['both_hands_confident_pct']:.1f}%")
    print("Assignment methods:",metadata["assignment_methods"])
    print("Source warnings:",result.warnings)
    print("Features:",out/"features_raw.npz")
    print("Metadata:",out/"metadata.json")
    print("No sign recognized yet: model-specific temporal adapters are the next stage.")


if __name__=="__main__":
    main()
