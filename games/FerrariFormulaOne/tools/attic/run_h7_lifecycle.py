from pathlib import Path
import json,os,subprocess,sys
r=Path(__file__).resolve().parents[1]
for arm in sys.argv[1:] or ['baseline','candidate']:
 for profile in os.environ.get('H7_LIVE_PROFILES','a1200-fast,030-50,040-40,060-50').split(','):
  build='render-h6' if arm=='baseline' else 'render-h7'
  env=dict(os.environ,H5_BUILD=str(r/'tmp/build'/build),C1_VARIANT='h7-'+arm)
  print('LIFECYCLE',profile,arm,flush=True)
  with (r/f'tmp/h7-live-{profile}-{arm}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/run_h7_live.py'),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
  print('PASS',profile,arm,flush=True)
