from pathlib import Path
import os,json,subprocess,sys,hashlib
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for profile in ('a1200-fast','a1200'):
 for variant,passes in (('verify',0),('verify',1),('verify',3),('lean',0)):
  name=f'{profile}-s3-v3-{variant}-p{passes}-fine';out=r/'tmp/step5'/name;slave=r/f'tmp/build/step5-s3/{variant}-p{passes}/fine.slave'
  old=json.loads((out/'result.json').read_text()) if (out/'result.json').exists() else {}
  if old.get('status')=='complete' and old.get('slave_sha256')==hashlib.sha256(slave.read_bytes()).hexdigest():continue
  env=dict(os.environ,**profiles[profile],LEAN=str(int(variant=='lean')),KICKSTART=os.environ['KICKSTART_A1200'],WHD_ARGS='CUSTOM1=1',SLAVE=str(slave))
  print('START',name,flush=True)
  subprocess.run([sys.executable,str(r/'tools/capture_step5_verify_split.py'),name],env=env,check=True)
