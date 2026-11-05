import os,sys,subprocess,json,shutil
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for idx,(name,build,script,cell,custom) in enumerate([
 ('latency','d-main-latency-build','latency_c.py','a1200-fast+cache',''),
 ('off-020','d-main-promote-build','check_a.py','a1200-fast','CUSTOM2=0'),
 ('off-040','d-main-promote-build','check_a.py','040-25','CUSTOM2=0')]):
 out=root/f'tmp/d-public-extra-v2-{name}';out.mkdir();env=config(cell);env.update(SLAVE=str(root/'tmp'/build/('RoadRash-verify.slave' if name=='latency' else 'RoadRash.slave')),WHD_ARGS=custom,DEBUG_PORT=str(27480+idx))
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/'+script,str(out)]+([] if name=='latency' else ['--normal']),env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 finally:cleanup(out)
 print(name,p.returncode,flush=True);assert not p.returncode
