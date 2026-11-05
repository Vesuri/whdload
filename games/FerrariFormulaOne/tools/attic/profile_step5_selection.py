from pathlib import Path
import os,subprocess,sys,json,hashlib
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for profile,lo,hi in (('a1200','1b0f50','1b1540'),('a1200-fast','5b2f50','5b3540')):
 for mode in ('control','fine'):
  slave=r/'tmp/build/step5-selection-elapsed'/(mode+'.slave');name=profile+'-selection-profile-'+mode;out=r/'tmp/step5'/name
  previous=json.loads((out/'result.json').read_text()) if (out/'result.json').exists() else {}
  if previous.get('status')!='complete' or previous.get('slave_sha256')!=hashlib.sha256(slave.read_bytes()).hexdigest():
   e=dict(os.environ,**profiles[profile],WHD_ARGS='CUSTOM1=1 CUSTOM2=1',SLAVE=str(slave),KICKSTART=os.environ['KICKSTART_A1200'])
   subprocess.run([sys.executable,str(r/'tools/capture_step5_profile.py'),name],env=e,check=True)
  for tool,args in (('analyze_step5_profile.py',[]),('percar_step5_profile.py',[lo,hi]),('classify_step5_profile.py',[lo,hi])):
   subprocess.run([sys.executable,str(r/'tools'/tool),name,*args],check=True)
