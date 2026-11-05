import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');env=config('040-25');env.update(SLAVE=str(root/'tmp/d-public-assets-build/RoadRash.slave'),DEBUG_PORT='27576',WHD_ARGS='CUSTOM2=1');out=root/'tmp/d-asset-headers-public';out.mkdir()
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/asset_headers_d.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
finally:cleanup(out)
print(p.returncode)
