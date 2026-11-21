"""Verified local staging and immutable experiment metadata."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def safe(root,name):
    p=PurePosixPath(name);target=Path(root)/p
    if p.is_absolute() or '..' in p.parts or not target.resolve().is_relative_to(Path(root).resolve()):raise ValueError('Unsafe path')
    return target


def stage(source,target,digest):
    source,target=Path(source),Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and sha(target)==digest:return
    temp=target.with_name(target.name+'.partial');shutil.copyfile(source,temp)
    if sha(temp)!=digest:raise ValueError(f'Checksum mismatch: {source}')
    temp.replace(target)


def stage_cache(source,target,expected_config):
    source,target=Path(source),Path(target)
    stage(source/'cache.json',target/'cache.json',expected_config)
    success=json.loads((source/'_SUCCESS').read_text())
    if success['config_sha256']!=expected_config:raise ValueError('Cache not completed with expected config')
    stage(source/'SHA256SUMS',target/'SHA256SUMS',success['checksums_sha256'])
    sums={name:h for h,name in (line.split(maxsplit=1) for line in (target/'SHA256SUMS').read_text().splitlines())}
    for name in ['label_map.json','train.index.jsonl','val.index.jsonl']:
        stage(safe(source,name),safe(target,name),sums[name])
    records={s:[json.loads(l) for l in (target/f'{s}.index.jsonl').read_text().splitlines()] for s in ('train','val')}
    ids=set();signers={};labels=json.loads((target/'label_map.json').read_text())
    for split,rows in records.items():
        if not rows:raise ValueError('Empty split')
        signers[split]={r['sample']['signer_id'] for r in rows}
        for r in rows:
            key=tuple(r['sample'][k] for k in ('source_part','view','video_id'))
            if key in ids or r['sample']['split']!=split or labels[r['sample']['gloss']]!=r['label_id']:raise ValueError('Bad membership/labels')
            ids.add(key)
    if signers['train']&signers['val']:raise ValueError('Signer overlap')
    config=json.loads((target/'cache.json').read_text())
    membership={s:[r['sample'] for r in rows] for s,rows in records.items()}
    membership_bytes=(json.dumps(membership,ensure_ascii=False,sort_keys=True,separators=(',', ':'),allow_nan=False)+'\n').encode()
    if hashlib.sha256(membership_bytes).hexdigest()!=config['membership_sha256'] or sum(map(len,records.values()))!=success['clips']:raise ValueError('Cache membership/count mismatch')
    if config['labels']!=labels or sorted(labels.values())!=list(range(len(labels))):raise ValueError('Bad label IDs')
    for name in sorted({r['shard'] for rows in records.values() for r in rows}):
        print('Stage/verify:',name,flush=True)
        stage(safe(source,name),safe(target,name),sums[name])
    return config,records,labels
