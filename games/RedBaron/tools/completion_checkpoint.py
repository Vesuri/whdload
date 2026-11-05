"""One normal-bundle event window per machine at a phase checkpoint."""
import os,subprocess,sys
from pathlib import Path
phase=sys.argv[1]
for machine in ('a500','020','030','030-nommu','040','060'):
 out=f'tmp/prof/completion-{phase}-{machine}-1'
 env=dict(os.environ,BENCH_DEVELOPER='0',BENCH_EVENT_ONLY='1',BENCH_OPENING_ONLY='0')
 with Path(f'tmp/completion-{phase}-{machine}.log').open('w') as log:
  subprocess.run([sys.executable,'-B','tools/completion_matrix_case.py',machine,'1',out],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('CHECKPOINT CASE COMPLETE',phase,machine,flush=True)
