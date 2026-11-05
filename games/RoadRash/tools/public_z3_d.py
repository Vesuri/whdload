import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');env=config('030-50');env.update(FAST_KB='0',SLAVE=str(root/'tmp/d-main-promote-build/RoadRash.slave'),DEBUG_PORT='27488',WHD_ARGS='CUSTOM2=1');env['EXTRA_ARGS']+=' --uae_z3mem_size=8'
out=root/'tmp/d-public-z3';out.mkdir()
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/check_a.py',str(out),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
finally:cleanup(out)
print(p.returncode);assert not p.returncode
