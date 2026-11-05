from pathlib import Path
import os,sys,json,subprocess,hashlib
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for profile,lo,hi in (('a1200-fast','5b2f50','5b3540'),('a1200','1b0f50','1b1540')):
 for variant,build in (('s3','step5-s3/lean-p0'),('b3','step5-b3-v4/lean')):
  name=f'{profile}-b3-v4-matched-{variant}';slave=r/f'tmp/build/{build}/fine.slave';out=r/f'tmp/step5/{name}'
  e=dict(os.environ,**profiles[profile],KICKSTART=os.environ['KICKSTART_A1200'],SLAVE=str(slave),WHD_ARGS='CUSTOM1=1 CUSTOM2=1',START_LOOP='125')
  print('START',name,flush=True)
  subprocess.run([sys.executable,str(r/'tools/capture_step5_profile.py'),name],env=e,check=True)
  for tool,args in (('analyze_step5_profile.py',[]),('percar_step5_profile.py',[lo,hi]),('classify_step5_profile.py',[lo,hi])):
   with (out/(tool+'.txt')).open('w') as f:subprocess.run([sys.executable,str(r/'tools'/tool),name,*args],env=dict(os.environ,EXCLUDE_PACING='1',DROP_UPDATES='1',MAX_UPDATES='20'),stdout=f,check=True)
  print(name,json.loads((out/'profile.json').read_text())['mean_cycles'],flush=True)
