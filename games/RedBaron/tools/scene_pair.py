import os,subprocess,sys,json
from pathlib import Path
env=dict(os.environ,BENCH_BATCH_KEYS='1',BENCH_DEVELOPER='1',BENCH_FROZEN_SLAVE='tmp/prof/scene-direct-frozen-2/slave.slave')
for mode,mask in [('on',0x1b0ffa),('off',0xb0ffa)]:
 out=Path('tmp/prof/scene-direct-060-'+mode+'-2')
 with Path(str(out)+'.driver.log').open('w') as log:
  print('START',out,flush=True)
  subprocess.run([sys.executable,'-B','tools/scene_profile_case.py','060',hex(mask),str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 row=json.loads((out/'stages.json').read_text())
 print('COMPLETE',mode,row['fps'],row['timing']['summaries']['scene']['mean_ms'],flush=True)
