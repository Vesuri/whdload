import os,subprocess,sys,time
from pathlib import Path
log=Path('tmp/prof/scene-direct-verify-030-bank-2.driver.log');deadline=time.monotonic()+1200
while not log.exists() or 'SCENE TWINS PASS' not in log.read_text():
 if time.monotonic()>deadline:raise TimeoutError('Inspect owned scene validation')
 time.sleep(2)
env=dict(os.environ,BENCH_BATCH_KEYS='1',BENCH_DEVELOPER='0',BENCH_OMIT_CUSTOM2='1')
env.pop('BENCH_FROZEN_SLAVE',None)
for machine in ('a500','060'):
 out=Path('tmp/prof/scene-final-normal-'+machine+'-1')
 print('START',machine,flush=True)
 with Path(str(out)+'.driver.log').open('w') as log:
  subprocess.run([sys.executable,'-B','tools/scene_profile_case.py',machine,'0',str(out),'--check-only'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('PASS',machine,flush=True)
