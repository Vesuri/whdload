import os,subprocess,sys,json,time
from pathlib import Path
log=Path('tmp/prof/scene-direct-060-off-2.driver.log')
deadline=time.monotonic()+1200
while not log.exists() or 'RENDER PROFILE COMPLETE' not in log.read_text():
 if time.monotonic()>deadline:raise TimeoutError('Inspect the previous owned capture')
 time.sleep(2)
env=dict(os.environ,BENCH_BATCH_KEYS='1',BENCH_DEVELOPER='1',BENCH_FROZEN_SLAVE='tmp/prof/scene-direct-frozen-2/slave.slave')
for machine in ('030','040','030-nommu'):
 base=0xf0ffa if machine=='040' else 0xb0ffa
 for mode,mask in [('on',base|0x100000),('off',base)]:
  out=Path('tmp/prof/scene-direct-'+machine+'-'+mode+'-2')
  with Path(str(out)+'.driver.log').open('w') as log:
   print('START',out,flush=True)
   subprocess.run([sys.executable,'-B','tools/scene_profile_case.py',machine,hex(mask),str(out),'--groups','stages'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  row=json.loads((out/'stages.json').read_text())
  print('COMPLETE',machine,mode,row['fps'],row['timing']['summaries']['scene']['mean_ms'],flush=True)
for machine,fixture in [('040','transitions'),('030','bank')]:
 out=Path('tmp/prof/scene-direct-verify-'+machine+'-'+fixture+'-2')
 with Path(str(out)+'.driver.log').open('w') as log:
  print('START',out,flush=True)
  subprocess.run([sys.executable,'-B','tools/scene_verify.py',str(out),'--machine',machine,'--'+fixture],stdout=log,stderr=subprocess.STDOUT,check=True)
 print('COMPLETE',out,flush=True)
