from pathlib import Path
import os,sys,json,signal,shutil,hashlib,re
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);b=r/'tmp/build/step5-b6-div-test'
profiles=json.loads((r/'manifest/step3-profiles.json').read_text());expected=json.loads((b/'expected.json').read_text());originalkick=os.environ.get('KICKSTART','')
for profile,mode in (('a1200',1),):
 name='b6-div-oracle-'+profile+'-'+str(mode);out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True)
 listing=(b/('div'+str(mode)+'.list')).read_text()
 def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M).group(1),16)
 os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b/('div'+str(mode)+'.slave')),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'))
 if profile=='a1200':os.environ['KICKSTART']=os.environ['KICKSTART_A1200']
 elif originalkick:os.environ['KICKSTART']=originalkick
 s=Server('ff1measure',root=str(r),profile_window=False);log=[];result={'profile':profile,'implementation':mode,'scope':'native arithmetic oracle; startup warp; not performance validation','expected':expected}
 try:
  g=s.boot()
  def cmd(c):
   v=g.cmd(c,timeout=180);log.append(c+'\n'+v);return v
  def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
  cmd('break *0x65174');assert 'Breakpoint' in cmd('continue')
  probe=val('*(unsigned int*)0x654e8')-sym('barrier')
  result['probe']={n:val(f'*(unsigned int*){probe+sym(n)}') for n in ('installed','checked','error')}
  if result['probe']['error']:
   result['failure']=cmd(f'x/5wx {probe+sym("failed_case")}');result['outputs']=cmd(f'x/3wx {probe+sym("outputs")}')
  result['status']='passed' if result['probe']==dict(installed=1,checked=expected['comparisons'],error=0) else 'failed'
  result['source_sha256']=hashlib.sha256((r.parent.parent/'Games/FerrariFormulaOne_Math.s').read_bytes()).hexdigest()
  result['slave_sha256']=hashlib.sha256(Path(os.environ['SLAVE']).read_bytes()).hexdigest()
  shutil.copy(r/'amiga/.run/launch.json',out/'launch.json');(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(name,result['status'],result.get('failure',''),flush=True)
  assert result['status']=='passed',result
 finally:
  (out/'capture.log').write_text('\n'.join(log))
  if s.g:s.g.p.kill()
  try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except (ProcessLookupError,FileNotFoundError):pass
