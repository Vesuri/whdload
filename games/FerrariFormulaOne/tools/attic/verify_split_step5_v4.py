from pathlib import Path
import os,json,subprocess,sys,hashlib
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for p,modes in (('a1200',('fine',)),('a1200-fast',('fine',))):
 for mode in modes:
  name=p+'-verify-split-v4-lean-'+mode;out=r/'tmp/step5'/name
  if (out/'result.json').exists():
   previous=json.loads((out/'result.json').read_text())
   if previous.get('status')=='complete' and previous.get('slave_sha256')==hashlib.sha256((r/'tmp/build/step5-verify-split-v4/lean'/(mode+'.slave')).read_bytes()).hexdigest():continue
  e=dict(os.environ,**profiles[p],LEAN='1',WHD_ARGS='CUSTOM1=1',SLAVE=str(r/'tmp/build/step5-verify-split-v4/lean'/(mode+'.slave')))
  if p!='a500':e['KICKSTART']=os.environ['KICKSTART_A1200']
  print('START',name,flush=True);subprocess.run([sys.executable,str(r/'tools/capture_step5_verify_split.py'),name],env=e,check=True)
