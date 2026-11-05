import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();tag=sys.argv[1];out=root/f'tmp/vertical-capture-{tag}';out.mkdir()
env=config('040-25');env.update(FSUAE=str(root/'tmp/b-gdb-passive-emulator/fs-uae'),SLAVE=str(root/'tmp/release-3.0b-final/RoadRash.slave'),WHD_ARGS='CUSTOM2='+('0' if tag=='off' else '1'),DEBUG_PORT='28600')
if tag=='original':env.update(SLAVE=str(root/'tmp/game/RoadRash/RoadRash.slave'),WHD_ARGS='')
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/invoke_e.py','tools/vertical_capture.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
finally:cleanup(out)
print(tag,p.returncode)
