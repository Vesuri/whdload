#!/usr/bin/env python3
from pathlib import Path
import os,sys,json,subprocess
r=Path(__file__).resolve().parents[1];profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
def run(name,profile,arm=0,fields=500,**extra):
 p=r/'tmp/step3'/name
 if (p/'result.json').exists() and json.loads((p/'result.json').read_text()).get('status')=='complete':return
 e=dict(os.environ,**profiles[profile],WHD_ARGS=f'CUSTOM1={arm}',FIELDS=str(fields),OBSERVE='survey' if profile in ('a500','a1200','a1200-fast') else 'census')
 if profile!='a500':e['KICKSTART']=os.environ['KICKSTART_A1200']
 e.update(extra);print('START',name,flush=True)
 try:subprocess.run([sys.executable,str(r/('tools/ceiling_step3.py' if e.get('INSTANT_AT_ANCHOR')=='1' else 'tools/detail_step3.py')),name],env=e,check=True,timeout=280)
 except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as ex:print('FAILED',name,ex,flush=True);return
 subprocess.run([sys.executable,str(r/'tools/analyze_step3.py'),name],check=True)
 if e['OBSERVE']=='survey':subprocess.run([sys.executable,str(r/'tools/events_step3.py'),name],check=True)
for profile in ('a500','a1200','a1200-fast'):
 for arm in (0,1):run(f'detail-{profile}-c{arm}',profile,arm,FULL_TRACE='1')
control=str(r/'tmp/build/step3/control/FerrariFormulaOne.slave');omit=str(r/'tmp/build/step3/no-road-lines/FerrariFormulaOne.slave')
run('ceiling-control-c0','a1200-fast',0,SLAVE=control)
run('ceiling-control-c1','a1200-fast',1,SLAVE=control,FULL_TRACE='1')
run('ceiling-no-road-lines','a1200-fast',1,SLAVE=omit)
run('ceiling-instant-blitter','a1200-fast',1,SLAVE=control,INSTANT_AT_ANCHOR='1')
