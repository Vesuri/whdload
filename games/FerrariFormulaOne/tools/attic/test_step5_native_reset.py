from pathlib import Path
import os,sys,json,signal,shutil,struct,re,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r)
b=r/'tmp/build/step5-native-reset';profiles=json.loads((r/'manifest/step3-profiles.json').read_text());cases=json.loads((b/'cases.json').read_text())
for profile in ('a1200','a1200-fast'):
 for variant in ('control','bridge'):
  out=r/'tmp/step5'/('native-reset-'+profile+'-'+variant);out.mkdir(parents=True,exist_ok=True)
  if (out/'result.json').exists():
   previous=json.loads((out/'result.json').read_text())
   if previous.get('status')=='complete' and previous.get('slave_sha256')==hashlib.sha256((b/(variant+'.slave')).read_bytes()).hexdigest():continue
  listing=(b/(variant+'.list')).read_text()
  def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M).group(1),16)
  os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b/(variant+'.slave')),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'])
  s=Server('ff1measure',root=str(r),profile_window=False);log=[];result={'profile':profile,'variant':variant,'scope':'Forced native recovery reset fixture; warp enabled; not performance measurement'}
  try:
   g=s.boot()
   def cmd(c):
    try:
     v=g.cmd(c,timeout=60)
    except TimeoutError:
     for attempt in range(9):
      assert g.p.poll() is None,'Debugger exited while waiting'
      os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),0)
      print(profile,variant,'waiting for same debugger command',c,flush=True)
      try:
       v=g.read_until(g.sent,60).replace('(gdb) ','').strip();break
      except TimeoutError:
       if attempt==8:raise
    log.append(c+'\n'+v);return v
   def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
   cmd('break *0x65174');assert 'Breakpoint' in cmd('continue')
   probe=val('*(unsigned int*)0x654e8')-sym('barrier')
   cmd('delete');cmd(f'break *{probe+sym("contact_complete")}');assert 'Breakpoint' in cmd('continue')
   result['probe']={n:val(f'*(unsigned int*){probe+sym(n)}') for n in ('error','bridge_installed','bridge_contacts','bridge_resets','contact_first_count','contact_second_count')}
   start=probe+sym('contact_results');cmd(f'dump binary memory {out.relative_to(r)}/results.bin {start} {start+len(cases)*152}')
   result['source_sha256']=hashlib.sha256((r.parent.parent/'Games/FerrariFormulaOne_Position.s').read_bytes()).hexdigest();result['slave_sha256']=hashlib.sha256((b/(variant+'.slave')).read_bytes()).hexdigest()
   assert result['probe']['error']==0,result
   shutil.copy(r/'amiga/.run/launch.json',out/'launch.json');result['status']='complete';print(profile,variant,result['probe'],flush=True)
  except Exception as e:
   result['status']='failed';result['exception']=repr(e);raise
  finally:
   (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');(out/'capture.log').write_text('\n'.join(log))
   if s.g:s.g.p.kill()
   try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
   except (ProcessLookupError,FileNotFoundError):pass
