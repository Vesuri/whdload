"""Same-build controls: force only the candidate copy branch to its old loop."""
import subprocess,os,sys,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'tmp/step11'
for name in ['move16','movem','unrolled']:
 shutil.copyfile(out/name/'slave.slave',root/'tmp/build/release/TFX.Slave')
 env=dict(os.environ,FSUAE=str(root/'tmp/step9-emulator/fs-uae/fs-uae'),COPY_LISTING=str(out/f'{name}.lst'),COPY_OFF='1',TEST_SEED=str(out/f'{name}-seed'))
 with (out/f'{name}-off.log').open('w') as log:subprocess.run([sys.executable,'tools/step11_profile.py',str(out/f'{name}-off')],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 subprocess.run([sys.executable,'tools/step11_report.py',str(out/f'{name}-off'),str(out/f'{name}.lst')],cwd=root,check=True)
