import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae');out=root/'tmp/f-sort-selftest-v3';out.mkdir()
env=config('040-25');env.update(SLAVE=str(root/'tmp/f-sort-selftest-v3-build/RoadRash.slave'),RR_LISTING=str(root/'tmp/f-sort-selftest-v3-build/RoadRash.lst'),WHD_ARGS='CUSTOM2=1',DEBUG_PORT='27863')
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/sort_selftest_v2_f.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=600)
finally:cleanup(out)
print(p.returncode);assert not p.returncode
