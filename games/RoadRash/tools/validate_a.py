#!/usr/bin/env python3
"""Repeat the accepted tape and hashes, then prove that A4 rejects corrupted evidence."""
import argparse,json,subprocess,sys,tempfile,shutil
from pathlib import Path
from harness_a import ROOT
from compare_a import compare

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);args=ap.parse_args();root=args.out.resolve();root.mkdir(exist_ok=False,parents=True)
    reports=[]
    for mode in ('normal','verify','hash'):
        for repeat in (1,2):
            out=root/f'{mode}-{repeat}';script='check_a.py' if mode=='hash' else 'replay_a.py'
            flags=['--hash'] if mode=='hash' else ['--normal'] if mode=='normal' else []
            with (root/f'{mode}-{repeat}.log').open('w') as log:
                subprocess.run([sys.executable,str(ROOT/'tools'/script),str(out)]+flags,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
        result=compare(root/f'{mode}-1',root/f'{mode}-2',exact=True);reports.append(result)
        print(mode,'passed',result['passed'],flush=True)
        if not result['passed']:raise RuntimeError(json.dumps(result))
    negatives=[]
    for kind in ('distance','rank','crash','image','state'):
        mode='hash' if kind in ('distance','state') else 'verify';reference=root/f'{mode}-1'
        with tempfile.TemporaryDirectory(prefix='rr-negative-',dir=ROOT/'tmp') as tmp:
            candidate=Path(tmp)
            for p in reference.iterdir():
                if p.name in ('result.json','replay.json') or p.name.startswith('race-') and p.suffix=='.png':shutil.copyfile(p,candidate/p.name)
            if kind=='image':next(candidate.glob('race-*.png')).unlink()
            else:
                name='result.json' if mode=='hash' else 'replay.json';r=json.loads((candidate/name).read_text())
                if kind=='distance':r['distance490']*=1.02
                if kind=='state':r['after']['state_hash']^=1
                if kind=='rank':r['samples'][-1]['order'].reverse()
                if kind=='crash':r['crash_onsets_sampled']=[]
                (candidate/name).write_text(json.dumps(r))
            result=compare(reference,candidate,exact=True)
            if result['passed']:raise RuntimeError('negative control accepted: '+kind)
            negatives.append(dict(kind=kind,rejected=True,failed_checks=[k for k,v in result['checks'].items() if not v]))
    result=dict(passed=True,repeats=reports,negative_controls=negatives)
    (root/'validation.json').write_text(json.dumps(result,indent=2)+'\n');print('all repeat and rejection checks passed',flush=True)

if __name__=='__main__':main()
