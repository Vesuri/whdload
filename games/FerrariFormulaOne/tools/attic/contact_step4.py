from pathlib import Path
import os,json,subprocess,sys
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for p in ('a500','a1200','a1200-fast'):
 for mode in ('control','logic'):
  name=f'{p}-contact3-{mode}';out=r/'tmp/step4'/name
  if (out/'result.json').exists() and json.loads((out/'result.json').read_text()).get('status')=='complete':continue
  e=dict(os.environ,**profiles[p],WHD_ARGS='CUSTOM1=1',CONTACT='1',SLAVE=str(r/f'tmp/build/step4-contact-v3/{mode}.slave'))
  if p!='a500':e['KICKSTART']=os.environ['KICKSTART_A1200']
  print('START',name,flush=True)
  subprocess.run([sys.executable,str(r/'tools/capture_step4.py'),name],env=e,check=True,timeout=280)
