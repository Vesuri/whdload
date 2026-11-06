import subprocess,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];out=root/'tmp/step11'
for mode,name in [(2,'movem'),(3,'unrolled')]:
 with (out/f'build-{name}.log').open('w') as log:subprocess.run(['bash','tools/build.sh',f'-DSTEP11_COPY={mode}','-L',str(out/f'{name}.lst')],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
 with (out/f'{name}.log').open('w') as log:subprocess.run([sys.executable,'tools/step10_profile.py',str(out/name)],cwd=root,env=dict(os.environ,FSUAE=str(root/'tmp/step9-emulator/fs-uae/fs-uae')),stdout=log,stderr=subprocess.STDOUT,check=True)
 subprocess.run([sys.executable,'tools/step11_report.py',str(out/name),str(out/f'{name}.lst')],cwd=root,check=True)
