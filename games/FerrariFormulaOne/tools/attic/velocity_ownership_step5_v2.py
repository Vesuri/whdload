from pathlib import Path
import os,json,subprocess,sys,hashlib
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for p,modes in (('a1200',('control','bridge')),('a1200-fast',('control','bridge'))):
 for mode in modes:
  name=p+'-velocity-ownership-v2-'+mode;out=r/'tmp/step5'/name
  if (out/'result.json').exists():
   previous=json.loads((out/'result.json').read_text())
   if previous.get('status')=='complete' and previous.get('slave_sha256')==hashlib.sha256((r/'tmp/build/step5-velocity-ownership-v2'/(mode+'.slave')).read_bytes()).hexdigest():continue
  e=dict(os.environ,**profiles[p],WHD_ARGS='CUSTOM1=1',SLAVE=str(r/'tmp/build/step5-velocity-ownership-v2'/(mode+'.slave')))
  if p!='a500':e['KICKSTART']=os.environ['KICKSTART_A1200']
  print('START',name,flush=True);subprocess.run([sys.executable,str(r/'tools/capture_step5_velocity_ownership_v2.py'),name],env=e,check=True,timeout=280)
