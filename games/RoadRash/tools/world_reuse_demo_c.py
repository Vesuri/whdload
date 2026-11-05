import os,subprocess,sys
from pathlib import Path
from matrix_a import config
root=Path.cwd()
for i,name in enumerate(['fire','timeout']):
 env=config('040-25');env.update(SLAVE=str(root/'tmp/c-world-reuse-d4-build/RoadRash.slave'),WHD_ARGS='CUSTOM2=1',DEBUG_PORT=str(27152+i),RR_STACK_TEST='1')
 if name=='timeout':env['RR_DEMO_TIMEOUT']='1'
 subprocess.run([sys.executable,'tools/demo_c.py','tmp/c-world-reuse-d4-demo-'+name],env=env,check=True)
