"""Notebook 07 training recipes using the shared validation and checkpoint helpers."""
import hashlib
import json
from pathlib import Path
import random

import numpy as np
import torch
from torch import nn

from runner import evaluate, load_checkpoint, save_checkpoint


def make_optimizer(model, config):
    options = dict(lr=config['lr'], weight_decay=config['weight_decay'])
    if config.get('optimizer', 'AdamW') == 'SGD':
        return torch.optim.SGD(model.parameters(), **options, momentum=config['momentum'],
                               nesterov=config['nesterov'])
    return torch.optim.AdamW(model.parameters(), **options)


def make_scheduler(optimizer, config):
    name = config.get('scheduler', 'cosine')
    if name == 'plateau':
        return torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=config['scheduler_factor'],
            patience=config['scheduler_patience'])
    if name == 'multistep':
        return torch.optim.lr_scheduler.MultiStepLR(
            optimizer, milestones=config['milestones'], gamma=config['scheduler_factor'])
    return torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=config['epochs'])


def fit(model,train_loader,val_loader,config,run,device):
    run=Path(run);run.mkdir(parents=True,exist_ok=True)
    exact=json.dumps(config,ensure_ascii=False,sort_keys=True,indent=2)+'\n'
    if (run/'config.json').exists() and (run/'config.json').read_text()!=exact:raise ValueError('Resume config differs; use a new run')
    (run/'config.json').write_text(exact)
    fingerprint=hashlib.sha256(exact.encode()).hexdigest()
    model.to(device)
    optimizer = make_optimizer(model, config)
    scheduler = make_scheduler(optimizer, config)
    accumulation = config.get('accumulation_steps', 1)
    select_top1 = config.get('selection_metric') == 'validation_top1_then_loss'
    best_loss = float('inf')
    best=-1.;stale=0;start=0;history=[];generator=train_loader.generator
    if (run/'last.pt').exists():
        state=load_checkpoint(run/'last.pt')
        if state['config_sha256']!=fingerprint:raise ValueError('Checkpoint config mismatch')
        model.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer']);scheduler.load_state_dict(state['scheduler'])
        start=state['epoch']+1;best=state['best'];stale=state['stale'];history=state['history']
        best_loss = state.get('best_loss', float('inf'))
        torch.set_rng_state(state['rng_torch']);np.random.set_state(state['rng_numpy']);random.setstate(state['rng_python'])
        if device.type=='cuda' and state['rng_cuda'] is not None:torch.cuda.set_rng_state_all(state['rng_cuda'])
        generator.set_state(state['rng_loader'])
    for epoch in range(start,config['epochs']):
        if stale>=config['patience']:break
        model.train();total=0.;correct=0;count=0
        lr = optimizer.param_groups[0]['lr']
        window_samples = 0
        optimizer.zero_grad(set_to_none=True)
        for step, b in enumerate(train_loader, 1):
            x,real,time,target=(b[k].to(device) for k in ('x','real','time','label'))
            logits=model(x,real,time)
            loss=nn.functional.cross_entropy(logits,target)
            if not torch.isfinite(loss):raise ValueError('Non-finite train loss')
            samples = len(target)
            window_samples += samples
            (loss * samples if accumulation > 1 else loss).backward()
            if step % accumulation == 0 or step == len(train_loader):
                if accumulation > 1:
                    for parameter in model.parameters():
                        if parameter.grad is not None:
                            parameter.grad.div_(window_samples)
                if config['grad_clip'] is not None:
                    nn.utils.clip_grad_norm_(model.parameters(), config['grad_clip'],
                                             error_if_nonfinite=True)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                window_samples = 0
            total+=loss.item()*len(target);correct+=int((logits.argmax(-1)==target).sum());count+=len(target)
        if not count:raise ValueError('Empty training loader')
        val,_=evaluate(model,val_loader,device,config['classes'])
        if isinstance(scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
            scheduler.step(val['loss'])
        else:
            scheduler.step()
        score = val['top1'] if select_top1 else val['macro_f1']
        improved = score > best or (select_top1 and score == best and val['loss'] < best_loss)
        if improved:
            best, best_loss, stale = score, val['loss'], 0
        else:stale+=1
        history.append(dict(epoch=epoch+1,train_loss=total/count,train_top1=correct/count,val_loss=val['loss'],
                            val_top1=val['top1'],val_macro_f1=val['macro_f1'],val_worst_signer_top1=val['worst_signer_top1']))
        if 'scheduler' in config:
            history[-1].update(lr=lr, next_lr=optimizer.param_groups[0]['lr'])
        state=dict(model=model.state_dict(),optimizer=optimizer.state_dict(),scheduler=scheduler.state_dict(),epoch=epoch,
                   best=best,stale=stale,history=history,config_sha256=fingerprint,
                   rng_torch=torch.get_rng_state(),rng_numpy=np.random.get_state(),rng_python=random.getstate(),
                   rng_cuda=torch.cuda.get_rng_state_all() if device.type=='cuda' else None,rng_loader=generator.get_state())
        if select_top1:
            state['best_loss'] = best_loss
        if improved:save_checkpoint(run/'best.pt',state)
        save_checkpoint(run/'last.pt',state)
        (run/'history.json').write_text(json.dumps(history,indent=2))
        print(history[-1],flush=True)
    state=load_checkpoint(run/'best.pt');model.load_state_dict(state['model'])
    result,predictions=evaluate(model,val_loader,device,config['classes'])
    (run/'validation.json').write_text(json.dumps(dict(best_epoch=state['epoch']+1,**result),ensure_ascii=False,indent=2))
    (run/'validation_predictions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in predictions))
    return result
