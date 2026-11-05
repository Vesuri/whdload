import os,sys,subprocess
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
for i,(name,cell,toggle,expected) in enumerate([('aga-on','040-25',1,1),('aga-off','040-25',0,1),('ocs','a500-1m',1,0)]):
 env=config(cell);env.update(SLAVE=str(root/'tmp/border-blank-build/RoadRash.slave'),WHD_ARGS=f'Cache CUSTOM2={toggle}',DEBUG_PORT=str(27910+i),EXPECT_BLANK=str(expected))
 out=root/f'tmp/border-blank-{name}';out.mkdir()
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/public_invoke_d.py','tools/border_blank_probe.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=240)
 finally:cleanup(out)
 print(name,p.returncode,flush=True);assert not p.returncode
