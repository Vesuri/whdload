import os, subprocess, sys, json
from pathlib import Path
cases=[('060',0x30ffa,'off',2),('020',0xf1fff,'on',1),('020',0x71fff,'off',1),('030',0xb0ffa,'on',1),('030',0x30ffa,'off',1),('040',0xf0ffa,'on',1),('040',0x70ffa,'off',1),('030-nommu',0xb0ffa,'on',1),('030-nommu',0x30ffa,'off',1)]
env=dict(os.environ,BENCH_BATCH_KEYS='1',BENCH_DEVELOPER='1',BENCH_FROZEN_SLAVE='tmp/prof/artwork-sparse-a500-on-1/slave.slave')
for cpu,mask,mode,n in cases:
 out=Path(f'tmp/prof/artwork-sparse-{cpu}-{mode}-{n}')
 if out.exists():raise RuntimeError('Refuse existing '+str(out))
 log=Path(str(out)+'.driver.log')
 print('START',out,flush=True)
 with log.open('w') as f:
  subprocess.run([sys.executable,'-B','tools/artwork_profile_case.py',cpu,hex(mask),str(out)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 row=json.loads((out/'stages.json').read_text())
 print('COMPLETE',cpu,mode,'FPS',row['fps'],'cockpit',row['timing']['summaries']['cockpit']['mean_ms'],flush=True)
