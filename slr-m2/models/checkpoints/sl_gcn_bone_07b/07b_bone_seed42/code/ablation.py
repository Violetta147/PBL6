"""One-factor B0 ablations. Derived features use normalized XY + explicit validity."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import numpy as np
import torch
import dataset as b0

POSE_EDGES=((0,1),(0,2),(2,4),(1,3),(3,5),(0,6),(1,7),(6,7))
HAND_EDGES=((0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),
            (5,9),(9,10),(10,11),(11,12),(9,13),(13,14),(14,15),(15,16),
            (13,17),(0,17),(17,18),(18,19),(19,20))
BONE_EDGES=POSE_EDGES+tuple((u+start,v+start) for start in (8,29) for u,v in HAND_EDGES)
SPECS={
    'hand_local':dict(id='A1',frames=64,feature_dim=b0.FEATURE_DIM+126,description='B0 + wrist-centered, clip-median hand-scale local XY and 42 masks'),
    'temporal_96':dict(id='A2',frames=96,feature_dim=b0.FEATURE_DIM,description='B0 with uniform up to 96 frames'),
    'temporal_128':dict(id='A3',frames=128,feature_dim=b0.FEATURE_DIM,description='B0 with uniform up to 128 frames'),
    'bone':dict(id='A4',frames=64,feature_dim=b0.FEATURE_DIM+len(BONE_EDGES)*3,description='B0 + directed XY bone vectors and edge masks'),
    'motion':dict(id='A5',frames=64,feature_dim=b0.FEATURE_DIM+150,description='B0 + XY velocity in real seconds with uninterrupted-valid-interval masks'),
}


def selected_indices(t, frames):
    return np.rint(np.linspace(0,t-1,frames)).astype(np.int64) if t>=frames else np.arange(t)


def hand_local(a):
    h=np.asarray(a['xy'])[:,8:].reshape(-1,2,21,2)
    valid=np.asarray(a['usable_mask'])[:,8:].reshape(-1,2,21).astype(bool)
    imputed=np.asarray(a['imputed_mask'])[:,8:].reshape(-1,2,21).astype(bool)
    scale=np.full(2,np.nan)
    for side in range(2):
        refs=[0,5,9,13,17]
        trusted=(valid[:,side,refs]&~imputed[:,side,refs]).all(-1)
        lengths=np.median(np.linalg.norm(h[:,side,[5,9,13,17]]-h[:,side,0,None],axis=-1),axis=-1)
        trusted &= np.isfinite(lengths)&(lengths>1e-6)
        if trusted.any():scale[side]=np.median(lengths[trusted])
    mask=valid & valid[:,:,[0]] & np.isfinite(scale)[None,:,None]
    with np.errstate(invalid='ignore',divide='ignore'):
        local=(h-h[:,:,[0]])/scale[None,:,None,None]
    local=np.where(mask[...,None],local,0.).astype(np.float32)
    # Features calculated on original timeline before selecting frames. No rotation or fallback anchor.
    return np.concatenate([local.reshape(len(h),84),mask.reshape(len(h),42)],axis=-1).astype(np.float32)


def bone(a):
    xy=np.asarray(a['xy']);valid=np.asarray(a['usable_mask']).astype(bool)
    u,v=np.array(BONE_EDGES).T
    mask=valid[:,u]&valid[:,v]
    vectors=np.where(mask[...,None],xy[:,v]-xy[:,u],0.).astype(np.float32)
    return np.concatenate([vectors.reshape(len(xy),-1),mask],axis=-1).astype(np.float32)


def motion(a, idx):
    xy=np.asarray(a['xy']);valid=np.asarray(a['usable_mask']).astype(bool)
    times=np.asarray(a['timestamps'],np.float64);mapping=np.asarray(a['frame_indices'])
    n=len(idx);velocity=np.zeros((n,50,2),np.float32);mask=np.zeros((n,50),bool)
    # Prefix counts ensure two valid endpoints cannot bridge an invalid intermediate frame.
    bad=np.r_[np.zeros((1,50),int),np.cumsum(~valid,axis=0)]
    for k in range(1,n):
        left,right=idx[k-1:k+1];dt=times[right]-times[left]
        continuous=(mapping[right]-mapping[left])==(right-left)
        if dt>0 and np.isfinite(dt) and continuous:
            mask[k]=(bad[right+1]-bad[left])==0
            with np.errstate(invalid='ignore'):
                velocity[k]=np.where(mask[k,:,None],(xy[right]-xy[left])/dt,0.)
    return np.concatenate([velocity.reshape(n,100),mask],axis=-1).astype(np.float32)


def adapt(a, name):
    if name not in SPECS:raise ValueError(f'Unknown ablation: {name}; choose one of {list(SPECS)}')
    spec=SPECS[name];item=b0.adapt(a,spec['frames'])
    idx=selected_indices(len(a['xy']),spec['frames'])
    extra=None
    if name=='hand_local':extra=hand_local(a)[idx]
    elif name=='bone':extra=bone(a)[idx]
    elif name=='motion':extra=motion(a,idx)
    if extra is not None:
        padded=np.zeros((spec['frames'],extra.shape[-1]),np.float32);padded[:len(idx)]=extra
        item['x']=torch.cat([item['x'],torch.from_numpy(padded)],dim=-1)
    if item['x'].shape!=(spec['frames'],spec['feature_dim']) or not torch.isfinite(item['x']).all():
        raise ValueError('Invalid derived feature shape/values')
    return item


class AblationDataset(b0.CacheDataset):
    """Same verified tar/NPZ provenance as B0, without modifying its source/adapter."""
    def __init__(self,root,records,name,config_sha256=None,max_open_shards=48):
        if name not in SPECS:raise ValueError('Choose exactly one supported ablation')
        super().__init__(root,records,SPECS[name]['frames'],config_sha256,max_open_shards)
        self.name=name
    def __del__(self):
        if hasattr(self,'_tars'):self.close()
    def adapt_clip(self, arrays):
        return adapt(arrays, self.name)

    def __getitem__(self,i):
        record=self.records[i];name=record['shard'];path=(self.root/name).resolve()
        if not path.is_relative_to(self.root.resolve()):raise ValueError('Unsafe shard path')
        if name not in self._tars:
            self._tars[name]=tarfile.open(path);self._tars[name].getmembers()
            if len(self._tars)>self.max_open_shards:self._tars.popitem(last=False)[1].close()
        self._tars.move_to_end(name)
        payload=self._tars[name].extractfile(record['member']).read()
        if hashlib.sha256(payload).hexdigest()!=record['npz_sha256']:raise ValueError('NPZ hash mismatch')
        keys=['xy','usable_mask','observed_mask','imputed_mask','association_method',
              'normalization_fallback','timestamps','frame_indices']
        with np.load(io.BytesIO(payload),allow_pickle=False) as z:
            meta=json.loads(z['meta_json'].item());a={k:z[k] for k in keys}
        if meta['sample']!=record['sample'] or meta['label_id']!=record['label_id']:raise ValueError('Clip provenance mismatch')
        if self.config_sha256 and meta['config_sha256']!=self.config_sha256:raise ValueError('Wrong cache config')
        if len(a['xy'])!=record['frames']:raise ValueError('Frame count mismatch')
        item=self.adapt_clip(a)
        item.update(label=torch.tensor(record['label_id'],dtype=torch.long),
                    clip_id='_'.join(record['sample'][k] for k in ('source_part','view','video_id')),
                    signer_id=record['sample']['signer_id'])
        return item


def comparison(result, reference, config):
    """Validation deltas in percentage points; one seed is exploratory, not significance."""
    if result['class_support']!=reference['class_support'] or set(result['signer_top1'])!=set(reference['signer_top1']):
        raise ValueError('Validation support/signers differ from B0; do not compare subsets to full validation')
    keys=('top1','macro_f1','macro_signer_top1','worst_signer_top1')
    return dict(ablation=config['ablation'],baseline_run=config['baseline_run'],seed=config['seed'],
                frames=config['frames'],feature_dim=config['feature_dim'],parameters=config['parameters'],
                baseline_parameters=config['baseline_parameters'],
                environment_differences=config['environment_differences'],
                validation={k:dict(baseline=reference[k],ablation=result[k],delta_pp=100*(result[k]-reference[k])) for k in keys},
                signer_delta_pp={s:100*(result['signer_top1'][s]-reference['signer_top1'][s]) for s in reference['signer_top1']},
                interpretation='Single-seed validation screening; no test evaluation or statistical significance claim')
