from pathlib import Path
import subprocess,os,sys
r=Path(__file__).resolve().parents[1]
for arm in ['control','candidate']:
 b=r/('tmp/build/render-h5-matched-frames'+('-control' if arm=='control' else ''))
 env=dict(os.environ,H5_BUILD=str(b),C1_VARIANT='h5-matched-'+arm,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 with (r/f'tmp/h5-profile-a1200-fast-matched-{arm}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/capture_h5_profile.py'),'a1200-fast'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Captured',arm,flush=True)
subprocess.run([sys.executable,str(r/'tools/compare_h5_profile.py')],check=True)

for arm in ["control","candidate"]:
 subprocess.run([sys.executable,str(r/"tools/analyze_h5_text.py"),str(r/f"tmp/step5/c4-q03-render-profile-a1200-fast-h5-matched-{arm}")],check=True)
