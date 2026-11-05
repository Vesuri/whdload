#!/usr/bin/env python3
"""A4 gates and deterministic A1 repeat checks. Nonzero exit means a failed/unreviewed gate."""
import argparse,hashlib,json,sys
from pathlib import Path

def load(p,name):return json.loads((p/name).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def compare(reference,candidate,exact=False):
    checks={};details={}
    for name in ('result.json','replay.json'):
        if not (reference/name).exists() or not (candidate/name).exists():continue
        a,b=load(reference,name),load(candidate,name)
        checks[name+'/same_slave']=a['provenance']['slave_sha256']==b['provenance']['slave_sha256'] if exact else True
        if name=='result.json':
            relative=abs(b['distance490']-a['distance490'])/max(1,abs(a['distance490']))
            checks['distance_within_one_percent']=relative<=.01;details['distance_difference_percent']=100*relative
            if exact:
                checks['state_exact']=all(a[k]['state_sha256']==b[k]['state_sha256'] for k in ('initial','at490','end'))
                checks['frame_counts_exact']=a['rotation_frames']==b['rotation_frames']
                if a.get('hash_requested'):
                    checks['slave_hash_exact']=a['after']['hash_field']==b['after']['hash_field']==590 and a['after']['state_hash']==b['after']['state_hash']
        else:
            checks['same_tape']=a['tape']==b['tape']
            checks['rank_order']=a['samples'][-1]['order']==b['samples'][-1]['order'] and a['samples'][-1]['rank']==b['samples'][-1]['rank']
            checks['crash_count']=len(a['crash_onsets_sampled'])==len(b['crash_onsets_sampled'])
            checks['scenario_coverage']=len(b['crash_onsets_sampled'])==b['tape']['coverage']['crash_count'] and min(s['rank'] for s in b['samples'])<b['initial']['rank'] and any(e[1] in ('JOY2_LEFT','JOY2_RIGHT') for e in b['tape']['events'])
            if exact:
                checks['seed_and_initial_state_exact']=a['initial']['state_sha256']==b['initial']['state_sha256']
                checkpoints=set(a['tape']['screenshots'])|{a['tape']['start_field'],a['tape']['end_field']}
                checks['fixed_checkpoint_states_exact']=[(s['field'],s['state_sha256']) for s in a['samples'] if s['field'] in checkpoints]==[(s['field'],s['state_sha256']) for s in b['samples'] if s['field'] in checkpoints]
                details['intermediate_state_differences']=[x['field'] for x,y in zip(a['samples'],b['samples']) if x['state_sha256']!=y['state_sha256']]
    images=sorted(reference.glob('race-*.png'))
    checks['visual_scenes_exact']=bool(images) and all((candidate/p.name).exists() and sha(p)==sha(candidate/p.name) for p in images)
    if not checks['visual_scenes_exact']:details['visual_review']='Images differ or are missing; inspect matching race-field scenes. No automatic visual-equivalence claim.'
    if len(checks)==1:raise ValueError('no common result.json or replay.json')
    return dict(passed=all(checks.values()),checks=checks,details=details,reference=str(reference),candidate=str(candidate),exact=exact)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('reference',type=Path);ap.add_argument('candidate',type=Path);ap.add_argument('--exact',action='store_true');ap.add_argument('--out',type=Path)
    args=ap.parse_args();result=compare(args.reference,args.candidate,args.exact)
    data=json.dumps(result,indent=2)+'\n';print(data,end='')
    if args.out:args.out.write_text(data)
    if not result['passed']:sys.exit(1)

if __name__=='__main__':main()
