from pathlib import Path
import os,sys,subprocess,json,collections
r=Path(__file__).resolve().parents[1]
for arm in ['control','candidate']:
 tag='h7-dense-repeat-'+arm;b=r/('tmp/build/render-h7-dense'+('-control' if arm=='control' else ''))
 env=dict(os.environ,H5_BUILD=str(b),C1_VARIANT=tag,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
 print('REPEAT',arm,flush=True)
 with (r/f'tmp/{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h5_fps.py'),'a1200-fast'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 x=json.loads((r/f'tmp/step5/c4-q03-h5-fps-a1200-fast-{tag}/result.json').read_text());print(arm,x['fps'],x['mean_ms'],x['p95_ms'],collections.Counter(x['interval_fields']),x.get('intena_start'),flush=True)
