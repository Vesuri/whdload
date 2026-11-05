import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');env=config('040-25');env.update(SLAVE=str(root/'tmp/e-020-gate-build/RoadRash.slave'),DEBUG_PORT='27775',WHD_ARGS='CUSTOM2=1');out=root/'tmp/e-public-bus';out.mkdir()
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/bus_e.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
finally:cleanup(out)
print(p.returncode)
