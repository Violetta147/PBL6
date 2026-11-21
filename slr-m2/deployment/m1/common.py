import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'm1.v1'
DEFAULT_BUNDLE = ROOT / 'models/checkpoints/sl_gcn_bone_07b/07b_bone_seed42'

def sha(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()

def read(path):
    return json.loads(Path(path).read_text())

def write(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix+'.partial')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))
    temp.replace(path)

def check_bundle(bundle):
    bundle = Path(bundle).resolve()
    required = ['best.pt', 'best.pt.sha256', 'config.json', 'label_map.json']
    missing = [name for name in required if not (bundle/name).is_file()]
    if missing:
        raise ValueError(f'Download the 07b run into {bundle}. Missing: {", ".join(missing)}')
    config = read(bundle/'config.json')
    for key, expected in dict(model_variant='slgcn_bone_07b_revamped_100_150', stream='bone', feature_shape=[150,28,8]).items():
        if config.get(key) != expected:
            raise ValueError(f'07b config mismatch: {key}')
    labels = read(bundle/'label_map.json')
    if not isinstance(labels, dict) or sorted(labels.values()) != list(range(400)):
        raise ValueError('Expected 400 unique contiguous label IDs')
    digest = sha(bundle/'best.pt')
    if digest != (bundle/'best.pt.sha256').read_text().split()[0]:
        raise ValueError('Checkpoint checksum mismatch')
    hashes = config.get('code_hashes', {})
    if 'slgcn_bone_07b.py' not in hashes:
        raise ValueError('Missing frozen 07b code hashes')
    for name, expected in hashes.items():
        path = (bundle/'code'/name).resolve()
        if not path.is_relative_to(bundle/'code') or not path.is_file() or sha(path) != expected:
            raise ValueError(f'Frozen source missing or checksum mismatch: {name}')
    return dict(bundle=str(bundle), checkpoint_sha256=digest, config_sha256=sha(bundle/'config.json'), labels=labels)
