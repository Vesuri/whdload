import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for i,(name,build) in enumerate([('native','d-public-audio-v3-build'),('public','d-public-encoded-build')]):
 env=config('040-25');env.update(SLAVE=str(root/'tmp'/build/'RoadRash.slave'),DEBUG_PORT=str(27724+i),WHD_ARGS='CUSTOM2=1');out=root/'tmp'/('d-intro-decode-'+name);out.mkdir()
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/intro_decode_probe_d.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
 finally:cleanup(out)
 print(name,p.returncode,flush=True);assert not p.returncode
