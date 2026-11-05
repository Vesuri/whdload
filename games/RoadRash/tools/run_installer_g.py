import os,sys
sys.exit('run_installer_g.py needs the retired harness launcher (a private copy of amiga/run.sh with extra drives and its own startup-sequence); see docs/development.md')
from pathlib import Path
import drive
root=Path.cwd();base=root/'tmp/g-installer-native';drive.ROOT=base
os.environ.update(GAME=str(base/'fixture'),FSUAE=str(root/'tmp/b-gdb-passive-emulator/fs-uae'),DEBUG_PORT='28200')
s=drive.Session(base)
try:
 s.cmd('monitor fields 999')
 s.cmd('monitor mouse 90 127');s.cmd('monitor fields 4')
 s.cmd('monitor mouse 0 127');s.cmd('monitor fields 4');s.cmd('monitor mouse 90 127');s.cmd('monitor fields 4');s.cmd('monitor mouse 0 18');s.cmd('monitor fields 4');s.shot('pointer.png')
 for i in range(50):
  s.input('JOY1_FIRE_BUTTON',1);s.cmd('monitor fields 4');s.input('JOY1_FIRE_BUTTON',0)
  s.cmd('monitor fields 199');s.shot('installer.png')
  print('step',i,'done',len(list((base/'.run/dh1').glob('*.done'))),flush=True)
  if (base/'.run/dh1/all.done').exists():break
finally:s.quit()
