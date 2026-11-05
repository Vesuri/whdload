import os,sys,subprocess
from pathlib import Path
from matrix_a import config
root=Path(sys.argv[1]);root.mkdir(exist_ok=False)
for mode in ['keyboard','pad','demo-fire','demo-timeout']:
 env=config('a1200-fast+cache');env.update(DEBUG_PORT='26854',WHD_ARGS='NoCache CUSTOM2=1',RR_STACK_TEST='1')
 for key in ['RR_PAD','RR_DEMO_TIMEOUT']:env.pop(key,None)
 if mode=='pad':env['RR_PAD']='1'
 if mode=='demo-timeout':env['RR_DEMO_TIMEOUT']='1'
 script='demo_c.py' if mode.startswith('demo') else 'input_b.py'
 out=root/mode
 with (root/(mode+'.log')).open('w') as log:
  subprocess.run([sys.executable,'tools/'+script,str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
 print(mode,'passed',flush=True)
