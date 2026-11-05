"""Local fixture search: retain every attempt; no game-state injection."""
import json,subprocess,sys
from pathlib import Path
from harness_a import ROOT
base=json.loads((ROOT/'tools/fixtures/lap.json').read_text())
root=ROOT/'tmp/a-tape-search';root.mkdir(exist_ok=False)
for turn in (1140,1130,1150):
    tape=dict(base);tape['events']=[[100,'JOY2_UP',1],[600,'JOY2_RIGHT',1],[620,'JOY2_RIGHT',0],[800,'JOY2_LEFT',1],[820,'JOY2_LEFT',0],[1100,'JOY2_RIGHT',1],[turn,'JOY2_RIGHT',0],[turn,'JOY2_LEFT',1],[1500,'JOY2_LEFT',0],[1600,'JOY2_UP',0]]
    path=root/f'tape-{turn}.json';path.write_text(json.dumps(tape,indent=2)+'\n');ok=True
    for mode in ('normal','verify'):
        out=root/f'{turn}-{mode}'
        with (root/f'{turn}-{mode}.log').open('w') as log:
            subprocess.run([sys.executable,str(ROOT/'tools/replay_a.py'),str(out),'--tape',str(path),'--sample-step','10']+(['--normal'] if mode=='normal' else []),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        r=json.loads((out/'replay.json').read_text());covered=len(r['crash_onsets_sampled'])==1 and min(s['rank'] for s in r['samples'])<r['initial']['rank']
        print(turn,mode,r['crash_onsets_sampled'],covered,flush=True);ok &= covered
    if ok:
        (root/'accepted.txt').write_text(str(path)+'\n');break
else:raise RuntimeError('no shared fixture found in this search')
