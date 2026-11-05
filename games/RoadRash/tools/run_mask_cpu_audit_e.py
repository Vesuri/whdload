import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');env=config('040-25');env.update(SLAVE=str(root/'tmp/e-final-build/RoadRash.slave'),RR_LISTING=str(root/'tmp/e-final-build/RoadRash.lst'),DEBUG_PORT='27769',WHD_ARGS='CUSTOM2=1');out=root/'tmp/e-final-mask-audit';out.mkdir()
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/invoke_e.py','tools/mask_cpu_audit_e.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
finally:cleanup(out)
print(p.returncode)
