from pathlib import Path
import os,json,subprocess,sys
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for mode,script in (('menu-clock','menu_clock_step4.py'),('pause','pause_step4.py')):
 for p in ('a500','a1200-fast'):
  name=f'{p}-{mode}'+('-fixture' if mode=='pause' else '');out=r/'tmp/step4'/name
  if (out/'result.json').exists() and json.loads((out/'result.json').read_text()).get('status')=='complete':continue
  e=dict(os.environ,**profiles[p],WHD_ARGS='CUSTOM1=0')
  if p!='a500':e['KICKSTART']=os.environ['KICKSTART_A1200']
  print('START',name,flush=True)
  subprocess.run([sys.executable,str(r/'tools'/script),name],env=e,check=True,timeout=280)
