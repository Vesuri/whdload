import os,subprocess,sys
from pathlib import Path
from matrix_a import config
root=Path.cwd()
for i,(name,script,extra) in enumerate([
 ('keyboard','input_b.py',{}),('cd32','input_b.py',{'RR_PAD':'1'}),
 ('demo-fire','demo_c.py',{}),('demo-timeout','demo_c.py',{'RR_DEMO_TIMEOUT':'1'})]):
 env=config('040-25');env.update(SLAVE=str(root/'tmp/c-approved-lane-motion-build/RoadRash.slave'),WHD_ARGS='CUSTOM2=1',DEBUG_PORT=str(27236+i),RR_STACK_TEST='1');env.update(extra)
 subprocess.run([sys.executable,'tools/'+script,'tmp/c-approved-motion-'+name],env=env,check=True)
 print(name,'passed',flush=True)
