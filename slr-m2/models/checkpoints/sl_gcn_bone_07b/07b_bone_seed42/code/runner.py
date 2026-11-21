"""Deterministic B0 training, validation-only model selection, checkpoint resume."""
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import numpy as np
import torch
from torch import nn


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def save_checkpoint(path,state):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.partial');torch.save(state,temp);h=sha(temp);temp.replace(path)
    path.with_suffix(path.suffix+'.sha256').write_text(h)


def load_checkpoint(path):
    path=Path(path)
    if sha(path)!=path.with_suffix(path.suffix+'.sha256').read_text().strip():raise ValueError('Checkpoint checksum mismatch')
    return torch.load(path,map_location='cpu',weights_only=False)


def seed_all(seed):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark=False


def metrics(y,p,signers,classes):
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=int);signers=np.asarray(signers)
    cm=np.zeros((classes,classes),np.int64);np.add.at(cm,(y,p),1)
    tp=np.diag(cm);den=cm.sum(0)+cm.sum(1)
    f1=np.divide(2*tp,den,out=np.zeros(classes,float),where=den>0)
    by={s:float((p[signers==s]==y[signers==s]).mean()) for s in sorted(set(signers))}
    return dict(top1=float((y==p).mean()),macro_f1=float(f1.mean()),
                signer_top1=by,macro_signer_top1=float(np.mean(list(by.values()))),worst_signer_top1=min(by.values()),
                confusion_matrix=cm.tolist(),class_support=cm.sum(1).tolist())


def evaluate(model,loader,device,classes):
    model.eval();loss=0.;count=0;y=[];pred=[];signers=[];records=[]
    with torch.inference_mode():
        for b in loader:
            logits=model(b['x'].to(device),b['real'].to(device),b['time'].to(device));target=b['label'].to(device)
            loss+=nn.functional.cross_entropy(logits,target,reduction='sum').item();count+=len(target)
            p=logits.argmax(-1).cpu().tolist();y.extend(b['label'].tolist());pred.extend(p);signers.extend(b['signer_id'])
            records.extend(dict(clip_id=cid,signer_id=s,target=int(t),prediction=int(q)) for cid,s,t,q in zip(b['clip_id'],b['signer_id'],b['label'],p))
    if not count:raise ValueError('Empty validation loader')
    result=metrics(y,pred,signers,classes);result['loss']=loss/count
    return result,records


def fit(model,train_loader,val_loader,config,run,device):
    run=Path(run);run.mkdir(parents=True,exist_ok=True)
    exact=json.dumps(config,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    if (run/'config.json').exists() and (run/'config.json').read_text()!=exact:raise ValueError('Resume config differs; use a new run')
    (run/'config.json').write_text(exact)
    fingerprint=hashlib.sha256(exact.encode()).hexdigest()
    model.to(device);optimizer=torch.optim.AdamW(model.parameters(),lr=config['lr'],weight_decay=config['weight_decay'])
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=config['epochs'])
    best=-1.;stale=0;start=0;history=[];generator=train_loader.generator
    if (run/'last.pt').exists():
        state=load_checkpoint(run/'last.pt')
        if state['config_sha256']!=fingerprint:raise ValueError('Checkpoint config mismatch')
        model.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer']);scheduler.load_state_dict(state['scheduler'])
        start=state['epoch']+1;best=state['best'];stale=state['stale'];history=state['history']
        torch.set_rng_state(state['rng_torch']);np.random.set_state(state['rng_numpy']);random.setstate(state['rng_python'])
        if device.type=='cuda' and state['rng_cuda'] is not None:torch.cuda.set_rng_state_all(state['rng_cuda'])
        generator.set_state(state['rng_loader'])
    for epoch in range(start,config['epochs']):
        if stale>=config['patience']:break
        model.train();total=0.;correct=0;count=0
        for b in train_loader:
            x,real,time,target=(b[k].to(device) for k in ('x','real','time','label'))
            optimizer.zero_grad(set_to_none=True);logits=model(x,real,time)
            loss=nn.functional.cross_entropy(logits,target)
            if not torch.isfinite(loss):raise ValueError('Non-finite train loss')
            loss.backward();nn.utils.clip_grad_norm_(model.parameters(),config['grad_clip']);optimizer.step()
            total+=loss.item()*len(target);correct+=int((logits.argmax(-1)==target).sum());count+=len(target)
        if not count:raise ValueError('Empty training loader')
        val,_=evaluate(model,val_loader,device,config['classes']);scheduler.step()
        score=val['macro_f1'];improved=score>best
        if improved:best=score;stale=0
        else:stale+=1
        history.append(dict(epoch=epoch+1,train_loss=total/count,train_top1=correct/count,val_loss=val['loss'],
                            val_top1=val['top1'],val_macro_f1=score,val_worst_signer_top1=val['worst_signer_top1']))
        state=dict(model=model.state_dict(),optimizer=optimizer.state_dict(),scheduler=scheduler.state_dict(),epoch=epoch,
                   best=best,stale=stale,history=history,config_sha256=fingerprint,
                   rng_torch=torch.get_rng_state(),rng_numpy=np.random.get_state(),rng_python=random.getstate(),
                   rng_cuda=torch.cuda.get_rng_state_all() if device.type=='cuda' else None,rng_loader=generator.get_state())
        if improved:save_checkpoint(run/'best.pt',state)
        save_checkpoint(run/'last.pt',state)
        (run/'history.json').write_text(json.dumps(history,indent=2))
        print(history[-1],flush=True)
    state=load_checkpoint(run/'best.pt');model.load_state_dict(state['model'])
    result,predictions=evaluate(model,val_loader,device,config['classes'])
    (run/'validation.json').write_text(json.dumps(dict(best_epoch=state['epoch']+1,**result),ensure_ascii=False,indent=2))
    (run/'validation_predictions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in predictions))
    return result
