"""Run frozen model code in a dedicated subprocess to isolate training imports."""
import sys
import time
from pathlib import Path
import numpy as np
from .common import ROOT, check_bundle, write, sha


def classify(bundle, video, output):
    identity = check_bundle(bundle)
    sys.path.insert(0, str(Path(bundle).resolve()/'code'))
    import torch
    import slgcn_bone_07b as frozen
    import architecture_models
    sys.path.extend([str(ROOT/'extraction'), str(ROOT/'preprocessing')])
    import extract_raw
    import rescue_candidates
    import pilot_extraction
    import pilot
    import pair_guard
    from .common import read
    started = time.perf_counter()
    full, meta = extract_raw.extract_video(video, read(ROOT/'extraction/raw_extraction.json'))
    policy = read(ROOT/'extraction/rescue_policy.json')
    profile = rescue_candidates.detector_profile(full, meta['fps']) | {'view': 'front'}
    crop = None
    if rescue_candidates.selected(profile, policy):
        roi = pilot_extraction.upper_body_crop(full, meta['width'], meta['height'], padding=.6)
        crop, _ = rescue_candidates.extract_crop(video, full, meta, policy, roi)
    association = read(ROOT/'extraction/association_policy.json')
    association['ambiguity_margin'] = .001
    arrays, qc = pilot.process(full, crop, meta, association, pair_guard_policy=pair_guard.POLICY)
    source = object.__new__(frozen.BoneSequenceDataset)
    item = source.adapt_clip(arrays)
    class One:
        def __len__(self):
            return 1
        def __getitem__(self, index):
            return {key: value.clone() for key, value in item.items()}
    item = frozen.BoneWindowDataset(One(), training=False)[0]
    output = Path(output)
    tensor_path = output/'input.npz'
    np.savez_compressed(tensor_path, **{key: value.numpy() for key, value in item.items()})
    np.savez_compressed(output/'normalized.npz', xy=arrays['xy'], usable_mask=arrays['usable_mask'],
                        observed_mask=arrays['observed_mask'], imputed_mask=arrays['imputed_mask'])
    preprocess_seconds = time.perf_counter()-started
    model = architecture_models.build_model('sl_gcn', 400)
    checkpoint = torch.load(Path(bundle)/'best.pt', map_location='cpu', weights_only=False)
    model.load_state_dict(checkpoint['model'])
    model.float().eval()
    # Reload the exported artifact so the inspector and model consume identical values.
    with np.load(tensor_path, allow_pickle=False) as saved:
        inputs = [torch.from_numpy(saved[key]).unsqueeze(0) for key in ('x','real','time')]
    started = time.perf_counter()
    with torch.inference_mode():
        logits = model(*inputs)[0]
        if not torch.isfinite(logits).all():
            raise ValueError('Non-finite model output')
        scores, indices = logits.softmax(-1).topk(5)
    labels = {value:key for key,value in identity.pop('labels').items()}
    write(output/'prediction.json', dict(schema_version='m1.v1', model=identity,
          input_sha256=sha(tensor_path), preprocessing_seconds=preprocess_seconds,
          inference_seconds=time.perf_counter()-started, qc=qc, crop_rescue=crop is not None,
          source_frames=len(arrays['xy']), repeated_positions=max(0,150-len(arrays['xy'])),
          truncated_frames=max(0,len(arrays['xy'])-150),
          top5=[dict(label=labels[index], label_id=index, score=score)
                for index,score in zip(indices.tolist(),scores.tolist())]))

if __name__ == '__main__':
    classify(*sys.argv[1:])
