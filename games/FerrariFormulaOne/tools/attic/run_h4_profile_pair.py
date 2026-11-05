from pathlib import Path
import subprocess,os,sys
r=Path(__file__).resolve().parents[1]
for arm in ['control','candidate']:
 b=r/('tmp/build/render-h4-matched-frames'+('-control' if arm=='control' else ''))
 env=dict(os.environ,H4_BUILD=str(b),C1_VARIANT='h4-matched-'+arm,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 with (r/f'tmp/h4-profile-a1200-fast-matched-{arm}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/capture_h4_profile.py'),'a1200-fast'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 print('Captured',arm,flush=True)
subprocess.run([sys.executable,str(r/'tools/compare_h4_profile.py')],check=True)

for arm in ["control","candidate"]:
 subprocess.run([sys.executable,str(r/"tools/analyze_h4_text.py"),str(r/f"tmp/step5/c4-q03-render-profile-a1200-fast-h4-matched-{arm}")],check=True)
