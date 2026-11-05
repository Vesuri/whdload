from pathlib import Path
import os,sys,json,signal,hashlib,struct,re
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);b=r/'tmp/build/step5-selection';profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
kick500=os.environ['KICKSTART']
listing=(b/'fine.list').read_text()
def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M)[1],16)
# Identical passive load observer, original WHDLoad entry; selection never called.
control=bytearray((b/'fine.slave').read_bytes());control[32+24:32+26]=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()[32+24:32+26];(b/'control.slave').write_bytes(control)
control020=bytearray((b/'fine020.slave').read_bytes());control020[56:58]=control[56:58];(b/'control020.slave').write_bytes(control020)
for profile in ('a500','a500-fast','a1200','a1200-fast'):
 for mode,custom in (('control',0),('fine',0),('fine',1)):
  name=f'{profile}-selection-{mode}-c2{custom}';out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);slave=b/(mode+('020' if profile.startswith('a1200') else '')+'.slave');sha=hashlib.sha256(slave.read_bytes()).hexdigest()
  if (out/'result.json').exists():
   prev=json.loads((out/'result.json').read_text())
   if prev.get('status')=='passed' and prev.get('slave_sha256')==sha:continue
  os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(slave),WARP='1',WINDOW='none',WHD_ARGS=f'CUSTOM1=1 CUSTOM2={custom}',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'))
  os.environ['KICKSTART']=(os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else kick500)
  s=Server('ff1measure',root=str(r),profile_window=False);log=[]
  try:
   g=s.boot()
   def cmd(c):
    try:v=g.cmd(c,timeout=60)
    except TimeoutError:
     for attempt in range(9):
      assert g.p.poll() is None
      os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),0)
      print(name,'waiting on same live command',flush=True)
      try:v=g.read_until(g.sent,60).replace('(gdb) ','').strip();break
      except TimeoutError:
       if attempt==8:raise
    log.append(c+'\n'+v);return v
   def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
   cmd('break *0x65174');cmd('ignore $bpnum 124');assert 'Breakpoint' in cmd('continue')
   assert val('*(unsigned short*)0x1bee8')==1
   probe=val('*(unsigned int*)0x654e8')-sym('barrier')
   values={n:val(f'*(unsigned int*){probe+sym("selection_"+n)}') for n in ('attn','custom2','expansion','path','interval','enabled')}
   expected=0 if custom==0 else (2 if profile=='a1200-fast' else 1)
   assert values['path']==expected and values['interval']=={0:0,1:100,2:20}[expected] and values['enabled']==0,values
   if mode=='fine':assert values['custom2']==custom
   cmd('monitor warp 0')
   for tick in (125,150,175):
    if tick!=125:cmd('ignore $bpnum 24');assert 'Breakpoint' in cmd('continue')
    cmd(f'dump binary memory {out.relative_to(r)}/loop{tick}.bin 0 0x80000')
    if tick>125:assert cmd('monitor warp-status')=='warp=0'
   result=dict(status='passed',profile=profile,mode=mode,custom2=custom,selection=values,slave_sha256=sha)
   (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(name,values,flush=True)
  finally:
   (out/'capture.log').write_text('\n'.join(log))
   if s.g:s.g.p.kill()
   try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
   except (ProcessLookupError,FileNotFoundError):pass
