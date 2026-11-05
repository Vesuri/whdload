import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');env=config('040-25');env.update(SLAVE=str(root/'tmp/d-main-promote-final-build/RoadRash.slave'),DEBUG_PORT='27496',WHD_ARGS='CUSTOM2=1');out=root/'tmp/d-raw-module-dma';out.mkdir()
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/raw_module_dma_d.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
finally:cleanup(out)
print(p.returncode)
