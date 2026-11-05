from pathlib import Path
import os,sys,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1]
for profile in ['a1200-fast','030-50','040-40','060-50']:
 for case in ['ownership','fault-set','fault-clear','schedule-fault','velocity-fault']:
  print('OWNERSHIP',profile,case,flush=True)
  result=r/f'tmp/step5/c4-q03-h7-ownership-{profile}-{case}/result.json'
  binary=r/f'tmp/build/render-h7-{case}/FerrariFormulaOne.slave'
  if result.exists():
   old=json.loads(result.read_text())
   if old.get('status')=='passed' and old.get('slave_sha256')==hashlib.sha256(binary.read_bytes()).hexdigest():
    print('REUSE hash-verified pass',flush=True);continue
  env=dict(os.environ,H5_BUILD=str(r/f'tmp/build/render-h7-{case}'),C1_VARIANT=case,RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
  with (r/f'tmp/h7-ownership-{profile}-{case}.log').open('w') as f:subprocess.run([sys.executable,str(r/'tools/test_h7_ownership.py'),profile],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
