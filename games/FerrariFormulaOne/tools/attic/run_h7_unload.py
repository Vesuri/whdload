from pathlib import Path
import os,sys,subprocess
r=Path(__file__).resolve().parents[1]
for profile in ['a1200-fast','030-50','040-40','060-50']:
 for bit in [0,64]:
  case='unload-'+str(bit);print('NATIVE UNLOAD',profile,bit,flush=True)
  env=dict(os.environ,H5_BUILD=str(r/f'tmp/build/render-h7-{case}'),C1_VARIANT=case,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
  with (r/f'tmp/h7-unload-{profile}-{bit}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h7_unload.py'),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
