import os,sys,subprocess,json
from pathlib import Path
from drive import ROOT
base=Path(sys.argv[1]);base.mkdir(parents=True,exist_ok=True)
for delta in (4,2,1):
    env=dict(os.environ,RR_B='1',SLAVE=str(ROOT/f'tmp/b4-delta{delta}-build/RoadRash-verify.slave'),DEBUG_PORT='3084',EXTRA_ARGS='--uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false --uae_blitter_cycle_exact=false')
    for tool,folder in [('check_a.py','straight'),('replay_a.py','tape')]:
        out=base/f'delta{delta}-{folder}';out.mkdir()
        with (out/'run.log').open('w') as log:
            r=subprocess.run([sys.executable,str(ROOT/'tools'/tool),str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
        print(delta,folder,r.returncode,flush=True)
        if r.returncode:raise RuntimeError(str(out))
