import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for i,cell in enumerate(['040-mmu','060-mmu']):
 env=config(cell);env.update(SLAVE=str(root/'tmp/f-functional-build/RoadRash-verify.slave'),DEBUG_PORT=str(27845+i),WHD_ARGS='MMU CUSTOM2=1',RR_STACK_TEST='1');env['EXTRA_ARGS']=env['EXTRA_ARGS'].replace('--uae_cpu_data_cache=false','--uae_cpu_data_cache=true')
 out=root/'tmp'/('f-final-dcache-'+cell);out.mkdir()
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/cache_mmu_policy_c.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 finally:cleanup(out)
 print(cell,p.returncode,flush=True);assert not p.returncode
