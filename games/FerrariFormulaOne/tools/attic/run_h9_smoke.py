from pathlib import Path
import os,sys,subprocess,json
r=Path(__file__).resolve().parents[1]
for arm in ['control','candidate']:
 b=r/('tmp/build/render-h9-grid'+('-control' if arm=='control' else ''));tag='h9-grid-'+arm
 env=dict(os.environ,H5_BUILD=str(b),C1_VARIANT=tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 print('Starting',tag,flush=True)
 with (r/f'tmp/{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h5_fps.py'),'040-40-bce'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 x=json.loads((r/f'tmp/step5/c4-q03-h5-fps-040-40-bce-{tag}/result.json').read_text());print(arm,x['fps'],x['mean_ms'],x['p95_ms'],flush=True)
