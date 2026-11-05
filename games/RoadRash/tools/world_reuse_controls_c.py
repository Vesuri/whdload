import os,subprocess,sys
from pathlib import Path
from matrix_a import config
root=Path.cwd();slave=root/'tmp/c-world-reuse-d4-build/RoadRash.slave'
for i,(name,script,pad,toggle) in enumerate([('off','world_reuse_off_c.py',False,0),('keyboard','input_b.py',False,1),('cd32','input_b.py',True,1)]):
 env=config('040-25');env.update(SLAVE=str(slave),WHD_ARGS=f'CUSTOM2={toggle}',DEBUG_PORT=str(27148+i),RR_STACK_TEST='1')
 if pad:env['RR_PAD']='1'
 subprocess.run([sys.executable,'tools/'+script,'tmp/c-world-reuse-d4-'+name],env=env,check=True)
