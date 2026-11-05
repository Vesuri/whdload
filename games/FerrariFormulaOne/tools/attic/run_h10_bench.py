from pathlib import Path
import os,sys,subprocess,json
r=Path(__file__).resolve().parents[1]
for p in ['040-40-bce','060-50-bce','030-50-trace-bce']:
 for arm in ['control','candidate']:
  tag='h10-micro-'+arm;b=r/('tmp/build/render-h10-bench'+('-control' if arm=='control' else ''));env=dict(os.environ,H5_BUILD=str(b),C1_VARIANT=tag,HI25_FIELDS='12',RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache');out=r/f'tmp/step5/hi25-profile-{p}-{tag}'
  print('RUN',p,arm,flush=True)
  with (r/f'tmp/h10-{p}-{arm}.log').open('w') as f:
   subprocess.run([sys.executable,str(r/'tools/capture_h10_profile.py'),p],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
   subprocess.run([sys.executable,str(r/'tools/analyze_h9_trace.py'),str(out)],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
  print(json.loads((out/'hi25-analysis.json').read_text())['mean_after_wait_ms'],flush=True)
