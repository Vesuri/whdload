from pathlib import Path
import os,sys,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1]
def run(script,args,tag,extra={}):
 print('RUN',tag,flush=True)
 with (r/f'tmp/h11-v2-{tag}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools'/script),*args],env=dict(os.environ,**extra),stdout=f,stderr=subprocess.STDOUT,check=True)
 print('PASS',tag,flush=True)
oracle=r/'tmp/step5/c4-q03-h11-oracle-040-40-bce-h11-v2-candidate/result.json'
if not oracle.exists() or json.loads(oracle.read_text()).get('status')!='passed':
 run('test_h11_oracle.py',['040-40-bce'],'oracle',dict(H5_BUILD=str(r/'tmp/build/render-h11-v2-oracle'),C1_VARIANT='h11-v2-candidate'))
else:assert json.loads(oracle.read_text())['slave_sha256']==hashlib.sha256((r/'tmp/build/render-h11-v2-oracle/FerrariFormulaOne.slave').read_bytes()).hexdigest()
run('run_h11_live.py',['040-40'],'live',dict(H5_BUILD=str(r/'tmp/build/render-h11-v2'),C1_VARIANT='h11-v2-candidate'))
for case in ['fault-set','fault-clear']:
 run('test_h11_fault.py',['040-40'],case,dict(H5_BUILD=str(r/f'tmp/build/render-h11-v2-{case}'),C1_VARIANT=case,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache'))
for option in ['0','1']:run('test_h11_legacy.py',[],'legacy-'+option,dict(RELEASE_CUSTOM1=option,RELEASE_PROFILES='a1200-fast'))
subprocess.run([sys.executable,str(r/'tools/archive_h11.py')],check=True)
