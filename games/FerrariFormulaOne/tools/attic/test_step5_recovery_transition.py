from pathlib import Path
import os,sys,json,signal,hashlib,struct,re
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);b=r/'tmp/build/step5-recovery-transition';profiles=json.loads((r/'manifest/step3-profiles.json').read_text());expected=json.loads((b/'fine.json').read_text());listing=(b/'fine.list').read_text()
def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M).group(1),16)
for profile in ('a1200','a1200-fast'):
 out=r/'tmp/step5'/('recovery-transition-'+profile);out.mkdir(parents=True,exist_ok=True)
 sha=hashlib.sha256((b/'fine.slave').read_bytes()).hexdigest()
 if (out/'result.json').exists():
  prev=json.loads((out/'result.json').read_text())
  if prev.get('status')=='passed' and prev.get('slave_sha256')==sha:continue
 os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b/'fine.slave'),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'])
 s=Server('ff1measure',root=str(r),profile_window=False);log=[];result={'profile':profile,'scope':'Player/opponent recovery dispatcher and native refill loop with controlled guest state; not interactive handling or real-time acceptance','slave_sha256':sha}
 try:
  g=s.boot()
  def cmd(c):
   try:v=g.cmd(c,timeout=60)
   except TimeoutError:
    for attempt in range(9):
     assert g.p.poll() is None,'Debugger exited while awaiting the same command'
     os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),0)
     print(profile,'waiting on the same live debugger command',flush=True)
     try:
      v=g.read_until(g.sent,60).replace('(gdb) ','').strip();break
     except TimeoutError:
      if attempt==8:raise
   log.append(c+'\n'+v);return v
  def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
  cmd('break *0x65174');assert 'Breakpoint' in cmd('continue')
  probe=val('*(unsigned int*)0x654e8')-sym('barrier')
  cmd('delete');cmd(f'break *{probe+sym("recovery_test_stop")}');cmd(f'break *{probe+sym("velocity_stop")}')
  assert 'Breakpoint' in cmd('continue')
  result['pc']=val('$pc');result['error']=val(f'*(unsigned int*){probe+sym("error")}');result['complete']=val(f'*(unsigned int*){probe+sym("recovery_test_complete")}')
  start=probe+sym('recovery_test_results');cmd(f'dump binary memory {out.relative_to(r)}/results.bin {start} {start+len(expected)*128}')
  raw=(out/'results.bin').read_bytes();failures=[]
  for i,e in enumerate(expected):
   rec=raw[i*128:(i+1)*128];wanted=bytes.fromhex(e['expected_hex'])+struct.pack('>II',0,1)
   if rec!=wanted:failures.append({'index':i,'case':e,'actual_hex':rec.hex(),'expected_hex':wanted.hex()})
  result.update(cases=len(expected),failures=failures,status='passed' if result['complete']==1 and result['error']==0 and not failures else 'failed')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(profile,result['status'],len(failures),'failures',flush=True)
  assert result['status']=='passed',failures[:3]
 finally:
  (out/'capture.log').write_text('\n'.join(log))
  if s.g:s.g.p.kill()
  try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except (ProcessLookupError,FileNotFoundError):pass
