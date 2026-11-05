from pathlib import Path
import os,json,subprocess,sys
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
for p,modes in (('a500',('control','fast000','verify000')),('a1200',('control','cache')),('a1200-fast',('control','cache'))):
 for mode in modes:
  name=p+'-math-v4-'+mode;out=r/'tmp/step5'/name
  if (out/'result.json').exists() and json.loads((out/'result.json').read_text()).get('status')=='complete':continue
  e=dict(os.environ,**profiles[p],WHD_ARGS='CUSTOM1=1',SLAVE=str(r/'tmp/build/step5-math-v4'/(mode+'.slave')))
  if p!='a500':e['KICKSTART']=os.environ['KICKSTART_A1200']
  print('START',name,flush=True);subprocess.run([sys.executable,str(r/'tools/capture_step5_math.py'),name],env=e,check=True,timeout=280)
