from pathlib import Path
import os,sys,subprocess
r=Path(__file__).resolve().parents[1]
def run(script,args,tag,extra={}):
 print('RUN',tag,flush=True)
 with (r/f'tmp/h10-{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),*args],env=dict(os.environ,**extra),stdout=f,stderr=subprocess.STDOUT,check=True)
 print('PASS',tag,flush=True)
run('test_h10_oracle.py',['040-40-bce'],'oracle',dict(H5_BUILD=str(r/'tmp/build/render-h10-oracle'),C1_VARIANT='h10-candidate'))
run('run_h7_live.py',['040-40'],'live',dict(H5_BUILD=str(r/'tmp/build/render-h10'),C1_VARIANT='h10-candidate'))
run('test_h10_fault.py',['040-40'],'fault')
for option in ['0','1']:run('test_h10_legacy.py',[],'legacy-'+option,dict(RELEASE_CUSTOM1=option,RELEASE_PROFILES='a1200-fast'))
