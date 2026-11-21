"""Fixed uniform sampling from versioned NPZ-in-tar cache. No augmentation."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
from collections import OrderedDict
import numpy as np
import torch
from torch.utils.data import Dataset

FEATURE_DIM = 259  # XY(100), usable/observed/imputed(150), four association methods(8), fallback(1)


def adapt(a, frames=64):
    xy=np.asarray(a['xy']);t=len(xy)
    if t<1 or frames<1 or xy.shape!=(t,50,2):raise ValueError('Invalid clip/sampling shape')
    idx=np.rint(np.linspace(0,t-1,frames)).astype(np.int64) if t>=frames else np.arange(t)
    n=len(idx);real=np.zeros(frames,bool);real[:n]=True
    usable=a['usable_mask'][idx].astype(bool)
    selected=xy[idx]
    if not np.array_equal(np.isfinite(selected).all(-1),usable):raise ValueError('XY/usable mask mismatch')
    # Only normalized XY is zero-filled; all masks keep their original semantics.
    finite=np.where(usable[...,None],selected,0.).astype(np.float32).reshape(n,100)
    method=a['association_method'][idx]
    features=np.concatenate([finite,usable,a['observed_mask'][idx],a['imputed_mask'][idx],
                             method=='pose',method=='tracking',method=='ambiguous',method=='none',a['normalization_fallback'][idx,None]],axis=-1).astype(np.float32)
    x=np.zeros((frames,FEATURE_DIM),np.float32);x[:n]=features
    timestamps=np.asarray(a['timestamps'],np.float64)
    if not np.isfinite(timestamps).all() or (np.diff(timestamps)<=0).any():raise ValueError('Bad timestamps')
    elapsed=timestamps[idx]-timestamps[0];duration=float(timestamps[-1]-timestamps[0])
    time=np.zeros((frames,2),np.float32);time[:n,0]=elapsed
    time[:n,1]=elapsed/max(duration,1e-8)
    mapping=np.full(frames,-1,np.int64);mapping[:n]=np.asarray(a['frame_indices'])[idx]
    if not np.isfinite(x).all():raise ValueError('Non-finite model input')
    return dict(x=torch.from_numpy(x),real=torch.from_numpy(real),time=torch.from_numpy(time),
                frame_indices=torch.from_numpy(mapping))


class CacheDataset(Dataset):
    def __init__(self, root, records, frames=64, config_sha256=None, max_open_shards=48):
        self.root=Path(root);self.records=records;self.frames=frames
        self.config_sha256=config_sha256;self.max_open_shards=max_open_shards;self._tars=OrderedDict()
    def __len__(self):return len(self.records)
    def __getstate__(self):
        state=self.__dict__.copy();state['_tars']=OrderedDict();return state
    def close(self):
        for tar in self._tars.values():tar.close()
        self._tars.clear()
    def __del__(self):self.close()
    def __getitem__(self,i):
        r=self.records[i];name=r['shard'];path=(self.root/name).resolve()
        if not path.is_relative_to(self.root.resolve()):raise ValueError('Unsafe shard path')
        if name not in self._tars:
            self._tars[name]=tarfile.open(path);self._tars[name].getmembers()
            if len(self._tars)>self.max_open_shards:self._tars.popitem(last=False)[1].close()
        self._tars.move_to_end(name)
        payload=self._tars[name].extractfile(r['member']).read()
        if hashlib.sha256(payload).hexdigest()!=r['npz_sha256']:raise ValueError('NPZ hash mismatch')
        keys=['xy','usable_mask','observed_mask','imputed_mask','association_method',
              'normalization_fallback','timestamps','frame_indices']
        with np.load(io.BytesIO(payload),allow_pickle=False) as z:
            meta=json.loads(z['meta_json'].item());a={k:z[k] for k in keys}
        if meta['sample']!=r['sample'] or meta['label_id']!=r['label_id']:raise ValueError('Clip provenance mismatch')
        if self.config_sha256 and meta['config_sha256']!=self.config_sha256:raise ValueError('Wrong cache config')
        if len(a['xy'])!=r['frames']:raise ValueError('Frame count mismatch')
        item=adapt(a,self.frames)
        item.update(label=torch.tensor(r['label_id'],dtype=torch.long),
                    clip_id='_'.join(r['sample'][k] for k in ('source_part','view','video_id')),
                    signer_id=r['sample']['signer_id'])
        return item
