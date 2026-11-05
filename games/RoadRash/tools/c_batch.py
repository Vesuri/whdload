"""Bounded sequential C checks with explicit, isolated configurations."""
import os,sys,subprocess,json
from pathlib import Path
from harness_a import ROOT
base=Path(sys.argv[1]).resolve();base.mkdir(parents=True,exist_ok=True)
suite=sys.argv[2];build=ROOT/'tmp/c-build'
fast='--uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false --uae_blitter_cycle_exact=false'
jobs=[]
if suite=='functional':
    for mode in (2,3,4):
        jobs.append((f'fixed{mode}','check_a.py',[],dict(WHD_ARGS=f'CUSTOM3={mode}',EXTRA_ARGS=fast,SLAVE=str(build/'RoadRash-verify.slave'))))
elif suite=='replay':
    for mode in (0,4):jobs.append((f'mode{mode}','replay_a.py',['--normal'],dict(WHD_ARGS=f'CUSTOM3={mode}',SLAVE=str(build/'RoadRash.slave'))))
elif suite=='input':
    for mode in (1,2,3,4):
        jobs.append((f'mode{mode}','input_b.py',[],dict(WHD_ARGS=f'CUSTOM3={mode}',SLAVE=str(build/'RoadRash.slave'))))
    jobs.append(('pad','input_b.py',[],dict(WHD_ARGS='CUSTOM3=1 CUSTOM2=3',RR_PAD='1',SLAVE=str(build/'RoadRash.slave'))))
else:raise ValueError(suite)
results=[]
for name,tool,args,extra in jobs:
    out=base/name;out.mkdir(exist_ok=False)
    env=dict(os.environ,**extra)
    with (out/'run.log').open('w') as log:
        try:r=subprocess.run([sys.executable,str(ROOT/'tools'/tool),str(out),*args],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240);rc=r.returncode
        except subprocess.TimeoutExpired:rc=124
    results.append(dict(name=name,returncode=rc));(base/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(results[-1],flush=True)
if any(r['returncode'] for r in results):sys.exit(1)
