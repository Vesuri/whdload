import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for tag in ['masks-all']:
 env=config('040-25');env.update(SLAVE=str(root/f'tmp/e-{tag}-fixed-build/RoadRash-verify.slave'),DEBUG_PORT='27752',WHD_ARGS='CUSTOM2=1');out=root/f'tmp/e-{tag}-frames';out.mkdir()
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/frame_probe_e.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
 finally:cleanup(out)
 print(tag,p.returncode,flush=True);assert not p.returncode
