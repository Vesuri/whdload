import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for i,kind in enumerate(['keyboard','pad']):
 out=root/f'tmp/d-native-main-{kind}';out.mkdir();env=config('a500-1m');env.update(FAST_KB='8192',SLAVE=str(root/'tmp/d-native-main-promote-build/RoadRash.slave'),DEBUG_PORT=str(27574+i),WHD_ARGS='CUSTOM2=1',RR_STACK_TEST='1')
 if kind=='pad':env['RR_PAD']='1'
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/input_b.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 finally:cleanup(out)
 print(kind,p.returncode,flush=True);assert not p.returncode
