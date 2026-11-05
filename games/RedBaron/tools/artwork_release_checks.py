import os, subprocess, sys
from pathlib import Path
env=dict(os.environ, BENCH_BATCH_KEYS='1', BENCH_DEVELOPER='0', BENCH_OMIT_CUSTOM2='1')
env.pop('BENCH_FROZEN_SLAVE',None)
for machine in ('a500','030'):
 out=Path('tmp/prof/artwork-final-normal-'+machine+'-1')
 print('START',machine,flush=True)
 with Path(str(out)+'.driver.log').open('w') as log:
  subprocess.run([sys.executable,'-B','tools/artwork_profile_case.py',machine,'0',str(out),'--check-only'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('PASS',machine,flush=True)
