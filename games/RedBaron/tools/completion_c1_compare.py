import os,sys,subprocess
from pathlib import Path
for machine,base in [('a500',0x31fbf),('020',0x31fbf),('030',0x30fba),('040',0x30fba),('060',0x30fba)]:
 for state,mask in [('off',base),('on',base|0x8000)]:
  out=f'tmp/prof/completion-c1-{machine}-{state}'
  env=dict(os.environ,BENCH_DEVELOPER='1',BENCH_OPENING_ONLY='1',BENCH_EVENT_ONLY='0',BENCH_FIELDS='2000',BENCH_BATCH_KEYS='1')
  with Path(f'tmp/completion-c1-{machine}-{state}.log').open('w') as log:
   subprocess.run([sys.executable,'-B','tools/completion_matrix_case.py',machine,str(mask),out],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
  print('C1 CASE COMPLETE',machine,state,flush=True)
