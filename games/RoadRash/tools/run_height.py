import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();tag=sys.argv[1];out=root/f'tmp/h1-{tag}';out.mkdir()
env=config('040-25');env.update(FSUAE=str(root/'tmp/b-gdb-passive-emulator/fs-uae'),SLAVE=str(root/'tmp/release-3.0b-final/RoadRash.slave'),WHD_ARGS='Cache CUSTOM2='+('0' if tag.startswith('off') else '1'),DEBUG_PORT=sys.argv[2])
if tag.startswith('original'):env.update(SLAVE=str(root/'tmp/game/RoadRash/RoadRash.slave'),WHD_ARGS='Cache')
if os.environ.get('HEIGHT_SLAVE'):env['SLAVE']=os.environ['HEIGHT_SLAVE']
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/invoke_e.py',os.environ.get('HEIGHT_PROBE','tools/height_trace.py'),str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
finally:cleanup(out)
print(tag,p.returncode)
