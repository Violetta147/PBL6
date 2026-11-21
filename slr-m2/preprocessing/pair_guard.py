"""Experimental v3 cross-source duplicate-pair guard; no raw/candidate deletion.

Geometry plus nearby-frame support is evidence of duplication, not ground truth.
All distances use aspect-correct XY; future frames make this policy offline.
"""
import itertools
import numpy as np

POLICY = dict(version='cross_source_pair_guard_v3', enabled=True,
              wrist_max=.4, joint_mean_max=.55, palm_mean_max=1., scale_ratio_max=2.5,
              support_window_seconds=.08, min_support_frames=1,
              temporal_match_max=1.5)
PALM = [0,5,9,13,17]


def metrics(p, q, aspect):
    p = p[:,:2]*[1,aspect]; q = q[:,:2]*[1,aspect]
    if not np.isfinite(p).all() or not np.isfinite(q).all():
        return np.full(5,np.inf)
    sizes = [np.median(np.linalg.norm(x[[5,9,13,17]]-x[0],axis=-1)) for x in (p,q)]
    if min(sizes) < 1e-6:
        return np.full(5,np.inf)
    scale = np.mean(sizes)
    delta = np.linalg.norm(p-q,axis=-1)/scale
    return np.array([delta[0],delta.mean(),delta[PALM].mean(),max(sizes)/min(sizes),scale])


def geometry_matches(m, policy):
    return bool(np.isfinite(m).all() and m[0]<=policy['wrist_max'] and m[1]<=policy['joint_mean_max']
                and m[2]<=policy['palm_mean_max'] and m[3]<=policy['scale_ratio_max'])


def detect_sequence(arrays, timestamps, aspect, policy):
    """Non-transitive, explicit conflicts; never infer A=C from A=B and B=C."""
    if set(policy) != set(POLICY) or policy['version'] != POLICY['version']:
        raise ValueError('Unknown pair guard policy')
    if type(policy['enabled']) is not bool:
        raise ValueError('Pair guard enabled must be boolean')
    for name in POLICY.keys()-{'version','enabled'}:
        if not np.isfinite(policy[name]) or policy[name] < 0:
            raise ValueError(f'Invalid pair guard parameter: {name}')
    if type(policy['min_support_frames']) is not int or policy['min_support_frames']<1:
        raise ValueError('Support must include at least one other frame')
    if not np.isfinite(aspect) or aspect<=0 or not np.isfinite(timestamps).all() or np.any(np.diff(timestamps)<=0):
        raise ValueError('Invalid aspect/timeline')
    offsets = arrays['hand_candidate_offsets']; frames=[]
    for t in range(len(timestamps)):
        start,end = offsets[t:t+2]; rows=[]
        if policy['enabled']:
            for i,j in itertools.combinations(range(end-start),2):
                fi,fj = arrays['fusion_full_indices'][start+np.array([i,j])]
                ci,cj = arrays['fusion_crop_indices'][start+np.array([i,j])]
                # Require separate full-only and crop-only representatives. Keep source evidence explicit.
                cross = (fi>=0 and ci<0 and fj<0 and cj>=0) or (fj>=0 and cj<0 and fi<0 and ci>=0)
                if not cross:
                    continue
                m=metrics(arrays['hand_candidate_xyz'][start+i],arrays['hand_candidate_xyz'][start+j],aspect)
                if geometry_matches(m,policy): rows.append((i,j,m))
        frames.append(rows)
    pairs=[]; evidence=[]; supports=[]; blocked=[]; pair_offsets=[0]
    for t,rows in enumerate(frames):
        start=offsets[t]
        for i,j,m in rows:
            p,q=arrays['hand_candidate_xyz'][start+np.array([i,j])]
            count=0
            neighbors=np.flatnonzero((np.abs(timestamps-timestamps[t])<=policy['support_window_seconds']+1e-9) & (np.arange(len(timestamps))!=t))
            for u in neighbors:
                others=frames[u]
                found=False
                for k,l,_ in others:
                    r,s=arrays['hand_candidate_xyz'][offsets[u]+np.array([k,l])]
                    # Match distinct detections between frames by whole-hand geometry, not raw candidate index.
                    direct=max(metrics(p,r,aspect)[1],metrics(q,s,aspect)[1])
                    reverse=max(metrics(p,s,aspect)[1],metrics(q,r,aspect)[1])
                    if min(direct,reverse)<=policy['temporal_match_max']:
                        found=True;break
                count+=int(found)
            pairs.append((i,j));evidence.append(m);supports.append(count)
            blocked.append(count>=policy['min_support_frames'])
        pair_offsets.append(len(pairs))
    return dict(duplicate_pair_offsets=np.array(pair_offsets,np.int64),
                duplicate_pair_indices=np.array(pairs,np.int32).reshape(-1,2),
                duplicate_pair_metrics=np.array(evidence,np.float32).reshape(-1,5),
                duplicate_pair_support=np.array(supports,np.int32),
                duplicate_pair_blocked=np.array(blocked,bool))


def conflicts_at(evidence, frame):
    start,end=evidence['duplicate_pair_offsets'][frame:frame+2]
    return {tuple(pair) for pair,blocked in zip(evidence['duplicate_pair_indices'][start:end],
                                              evidence['duplicate_pair_blocked'][start:end]) if blocked}


def associate_frame(base, candidates, worlds, pose, visibility, state, frame_index, aspect, policy, conflicts):
    """Solve over feasible pairs, excluding duplicate conflicts before computing margins.

    Known equivalent candidates on the same side are not distinct identity alternatives.
    All abstention/tracking semantics otherwise follow the original association policy.
    """
    if not conflicts:
        return base.associate_frame(candidates,worlds,pose,visibility,state,frame_index,aspect,policy)
    n=len(candidates);costs=np.full((2,n),np.inf);methods=['none','none'];limits=[0.,0.]
    for side,wrist in enumerate((4,5)):
        if np.isfinite(pose[wrist,:2]).all() and np.isfinite(visibility[wrist]) and visibility[wrist]>=policy['pose_visibility_min']:
            anchor=pose[wrist,:2];methods[side]='pose';limits[side]=policy['pose_max_distance']
        elif state[side] is not None and frame_index-state[side]['confirmed_frame']<=policy['max_tracking_gap_frames']:
            anchor=state[side]['xy'];methods[side]='tracking';limits[side]=policy['tracking_max_distance']
        else:continue
        d=np.linalg.norm((candidates[:,0,:2]-anchor)*[1,aspect],axis=-1)
        costs[side]=np.where(np.isfinite(d)&(d<=limits[side]),d,np.inf)
    def equivalent(i,j):return i>=0 and j>=0 and tuple(sorted((i,j))) in conflicts
    feasible=[]
    for pair in itertools.product(range(-1,n),repeat=2):
        if pair[0]>=0 and (pair[0]==pair[1] or equivalent(*pair)):continue
        value=sum(limits[s] if i<0 else costs[s,i] for s,i in enumerate(pair))
        if np.isfinite(value):feasible.append((float(value),pair))
    feasible.sort(key=lambda x:(x[0],x[1]));best,pair=feasible[0]
    result=dict(associated_hand_xyz=np.full((2,21,3),np.nan,np.float32),
                associated_hand_world_xyz=np.full((2,21,3),np.nan,np.float32),
                association_indices=np.full(2,-1,np.int32),association_proposed_indices=np.array(pair,np.int32),
                association_method=np.full(2,'none',dtype='<U12'),association_cost=np.full(2,np.nan,np.float32),
                association_margin=np.full(2,np.nan,np.float32),association_valid=np.zeros(2,bool))
    next_state=list(state)
    for side,idx in enumerate(pair):
        alternatives=[v for v,p in feasible if p[side]!=idx and not equivalent(idx,p[side])]
        margin=min(alternatives)-best if alternatives else float('inf')
        if np.isfinite(margin):result['association_margin'][side]=max(0.,margin)
        if methods[side]!='none' and margin<policy['ambiguity_margin']:
            result['association_method'][side]='ambiguous';continue
        if idx<0:continue
        result['association_indices'][side]=idx;result['association_method'][side]=methods[side]
        result['association_cost'][side]=costs[side,idx];result['association_valid'][side]=methods[side]=='pose'
        result['associated_hand_xyz'][side]=candidates[idx];result['associated_hand_world_xyz'][side]=worlds[idx]
        confirmed=frame_index if methods[side]=='pose' else state[side]['confirmed_frame']
        next_state[side]=dict(xy=candidates[idx,0,:2].copy(),confirmed_frame=confirmed)
    result['associated_hand_observed']=np.isfinite(result['associated_hand_xyz']).all(-1)
    return result,next_state


def associate_sequence(base, arrays, policy, aspect, evidence):
    state=[None,None];rows=[]
    for t in range(len(arrays['raw_pose_xyz'])):
        start,end=arrays['hand_candidate_offsets'][t:t+2]
        result,state=associate_frame(base,arrays['hand_candidate_xyz'][start:end],arrays['hand_candidate_world_xyz'][start:end],
                                     arrays['raw_pose_xyz'][t],arrays['raw_pose_visibility'][t],state,t,aspect,policy,conflicts_at(evidence,t))
        rows.append(result)
    return {key:np.stack([r[key] for r in rows]) for key in base.ASSOCIATION_SHAPES}
