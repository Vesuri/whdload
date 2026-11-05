import os,subprocess,sys,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
checks=[('040-mmu','040-mmu','cache_mmu_policy_c.py',True,{}),('060-mmu','060-mmu','cache_mmu_policy_c.py',True,{}),('keyboard','040-25','input_b.py',False,{}),('cd32','040-25','input_b.py',False,{'RR_PAD':'1'}),('demo','040-25','demo_c.py',False,{})]
for i,(name,cell,script,diag,extra) in enumerate(checks):
 env=config(cell);env.update(SLAVE=str(root/'tmp/e-final-build'/('RoadRash-verify.slave' if diag else 'RoadRash.slave')),DEBUG_PORT=str(27760+i),RR_STACK_TEST='1');env['WHD_ARGS']+=' CUSTOM2=1';env.update(extra)
 dest=root/'tmp'/('e-final-functional-'+name);dest.mkdir()
 try:
  with (dest/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/'+script,str(dest)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 finally:cleanup(dest)
 print(name,p.returncode,flush=True)
 assert p.returncode==0
