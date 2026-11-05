from pathlib import Path
import os,sys,subprocess,json
r=Path(__file__).resolve().parents[1]
for profile in ['a1200-fast','030-50','040-40','060-50']:
 for arm in ['control','candidate']:
  b=r/('tmp/build/render-h5-oracle-final'+('-control' if arm=='control' else ''));env=dict(os.environ,H5_BUILD=str(b),C1_VARIANT='final-'+arm,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
  print('Starting oracle/benchmark',profile,arm,flush=True)
  with (r/f'tmp/h5-oracle-{profile}-{arm}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h5_oracle.py'),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
  j=json.loads((r/f'tmp/step5/c4-q03-h5-oracle-{profile}-final-{arm}/result.json').read_text());print('Passed',profile,arm,j['checked'],j['us_per_glyph'],flush=True)
