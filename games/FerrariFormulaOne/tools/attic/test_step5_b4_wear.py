from pathlib import Path
import os,sys,json,signal,shutil,hashlib,struct,re
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r)
b=r/'tmp/build/step5-b4-wear-test';profiles=json.loads((r/'manifest/step3-profiles.json').read_text())

def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M).group(1),16)
for profile,variant in (('a1200','fine'),):
 expected=json.loads((b/(variant+'.json')).read_text());listing=(b/(variant+'.list')).read_text()
 out=r/'tmp/step5'/('b4-wear-'+profile);out.mkdir(parents=True,exist_ok=True)
 if (out/'result.json').exists():
  previous=json.loads((out/'result.json').read_text())
  if previous.get('status')=='passed' and previous.get('slave_sha256')==hashlib.sha256((b/(variant+'.slave')).read_bytes()).hexdigest():continue
 os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b/(variant+'.slave')),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'))
 if profile=='a1200':os.environ['KICKSTART']=os.environ['KICKSTART_A1200']
 s=Server('ff1measure',root=str(r),profile_window=False);log=[];result={'profile':profile,'scope':'continuous slip-wear guest unit tests; startup warp; not performance or integrated gameplay validation'}
 try:
  g=s.boot()
  def cmd(c):
   try:
    v=g.cmd(c,timeout=60)
   except TimeoutError:
    for attempt in range(9):
     assert g.p.poll() is None,'Debugger exited while waiting'
     os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),0)
     print(profile,'waiting for same debugger command',c,flush=True)
     try:
      v=g.read_until(g.sent,60).replace('(gdb) ','').strip();break
     except TimeoutError:
      if attempt==8:raise
   log.append(c+'\n'+v);return v
  def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
  cmd('break *0x65174');assert 'Breakpoint' in cmd('continue')
  probe=val('*(unsigned int*)0x654e8')-sym('barrier')
  result['installed']=val(f'*(unsigned int*){probe+sym("installed")}')
  start=probe+sym('results');cmd(f'dump binary memory {out.relative_to(r)}/results.bin {start} {start+len(expected)*16}')
  actual=list(struct.unpack('>'+str(len(expected)*4)+'I',(out/'results.bin').read_bytes()))
  result['cases']=[{'expected':e,'actual':actual[i*4:i*4+4],'passed':e['expected']==actual[i*4:i*4+4]} for i,e in enumerate(expected)]
  result['status']='passed' if result['installed']==1 and all(c['passed'] for c in result['cases']) else 'failed'
  result['source_sha256']=hashlib.sha256((r.parent.parent/'Games/FerrariFormulaOne_Wear.s').read_bytes()).hexdigest()
  result['slave_sha256']=hashlib.sha256((b/(variant+'.slave')).read_bytes()).hexdigest()
  shutil.copy(r/'amiga/.run/launch.json',out/'launch.json')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(profile,result['status'],flush=True)
  assert result['status']=='passed', {'failures':sum(not c['passed'] for c in result['cases']), 'first_failures':[c for c in result['cases'] if not c['passed']][:3]}
 finally:
  (out/'capture.log').write_text('\n'.join(log))
  if s.g:s.g.p.kill()
  try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except (ProcessLookupError,FileNotFoundError):pass
