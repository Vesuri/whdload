from pathlib import Path
import os,subprocess,sys,json,hashlib
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for profile,lo,hi in (('a1200','1b0f50','1b1540'),('a1200-fast','5b2f50','5b3540')):
 names=[]
 for mode in ('s2','s3'):
  slave=r/('tmp/build/step5-s2-scheduler-fix/lean/fine.slave' if mode=='s2' else 'tmp/build/step5-s3/lean-p0/fine.slave');name=profile+('-s3-profile-s2' if mode=='s2' else '-s3-v3-profile-s3');out=r/'tmp/step5'/name;names.append(name)
  previous=json.loads((out/'result.json').read_text()) if (out/'result.json').exists() else {}
  if previous.get('status')!='complete' or previous.get('slave_sha256')!=hashlib.sha256(slave.read_bytes()).hexdigest():
   e=dict(os.environ,**profiles[profile],WHD_ARGS='CUSTOM1=1 CUSTOM2=1',SLAVE=str(slave),KICKSTART=os.environ['KICKSTART_A1200'])
   subprocess.run([sys.executable,str(r/'tools/capture_step5_profile.py'),name],env=e,check=True)
  subprocess.run([sys.executable,str(r/'tools/analyze_step5_profile.py'),name],check=True,stdout=subprocess.DEVNULL)
 n=min(json.loads((r/'tmp/step5'/name/'profile.json').read_text())['complete_updates'] for name in names)
 for name in names:
  for tool,args in (('analyze_step5_profile.py',[]),('percar_step5_profile.py',[lo,hi]),('classify_step5_profile.py',[lo,hi])):
   with (r/'tmp/step5'/name/(tool+'.txt')).open('w') as log:
    subprocess.run([sys.executable,str(r/'tools'/tool),name,*args],check=True,env=dict(os.environ,MAX_UPDATES=str(n)),stdout=log)
  print(name,json.loads((r/'tmp/step5'/name/'profile.json').read_text())['mean_cycles'],'cycles',n,'matched updates',flush=True)
