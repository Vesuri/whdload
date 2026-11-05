from pathlib import Path
import os,subprocess,sys,json
r=Path(__file__).resolve().parents[1]
for arm in ['control','candidate']:
 b=r/('tmp/build/render-h13-probe'+('-control' if arm=='control' else ''));tag='h13-micro2-'+arm;p=r/f'tmp/step5/hi25-profile-040-40-bce-{tag}';env=dict(os.environ,H5_BUILD=str(b),C1_VARIANT=tag,HI25_FIELDS='12',RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 with (r/f'tmp/{tag}.log').open('w') as f:
  subprocess.run([sys.executable,str(r/'tools/capture_h13_profile.py'),'040-40-bce'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
  for name in ['analyze_hi25_profile.py','analyze_h8_calls.py']:
   subprocess.run([sys.executable,str(r/'tools'/name),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
 print(arm,json.loads((p/'hi25-analysis.json').read_text())['mean_after_wait_ms'],flush=True)
 subprocess.run([sys.executable,str(r/'tools/archive_h13.py')],check=True)
