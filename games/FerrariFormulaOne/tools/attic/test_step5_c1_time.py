from pathlib import Path
import os,sys,json,signal,shutil,hashlib,struct,re
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r)
b=r/'tmp/build/step5-c1-time-test';profiles=json.loads((r/'manifest/step3-profiles.json').read_text())
expected=json.loads((b/'expected.json').read_text());listing=(b/'test.list').read_text()
def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M).group(1),16)
for profile in ('a500','a1200'):
 out=r/'tmp/step5'/('c1-time-'+profile);out.mkdir(parents=True,exist_ok=True)
 os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b/'test.slave'),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'))
 if profile=='a1200':os.environ['KICKSTART']=os.environ['KICKSTART_A1200']
 s=Server('ff1measure',root=str(r),profile_window=False);log=[];result={'profile':profile,'scope':'timer guest unit tests; startup warp; not performance or integrated gameplay validation'}
 try:
  g=s.boot()
  def cmd(c):
   v=g.cmd(c,timeout=180);log.append(c+'\n'+v);return v
  def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
  cmd('break *0x65174');assert 'Breakpoint' in cmd('continue')
  probe=val('*(unsigned int*)0x654e8')-sym('barrier')
  result['probe']={n:val(f'*(unsigned int*){probe+sym(n)}') for n in ('installed','pause_due','early_result','unsupported_result','repeated_pause','repeated_resume','paused_consume')}
  assert result['probe']==dict(installed=1,pause_due=0,early_result=0xffffffff,unsupported_result=0,repeated_pause=0,repeated_resume=0,paused_consume=0xffffffff),result
  start=probe+sym('results');cmd(f'dump binary memory {out.relative_to(r)}/results.bin {start} {start+len(expected)*60}')
  actual=list(struct.unpack('>'+str(len(expected)*15)+'I',(out/'results.bin').read_bytes()))
  result['cases']=[]
  for i,e in enumerate(expected):
   values=actual[15*i:15*i+15];result['cases'].append(dict(e,actual=values,passed=values==e['expected']))
  start=probe+sym('context');cmd(f'dump binary memory {out.relative_to(r)}/context.bin {start} {start+56}')
  result['rejected_operations_preserve_context']=list(struct.unpack('>14I',(out/'context.bin').read_bytes()))==expected[-1]['expected'][:14]
  result['status']='passed' if all(c['passed'] for c in result['cases']) and result['rejected_operations_preserve_context'] else 'failed'
  result['source_sha256']=hashlib.sha256((r.parent.parent/'Games/FerrariFormulaOne_Time.s').read_bytes()).hexdigest()
  result['slave_sha256']=hashlib.sha256((b/'test.slave').read_bytes()).hexdigest()
  shutil.copy(r/'amiga/.run/launch.json',out/'launch.json')
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(profile,result['status'],flush=True)
  assert result['status']=='passed',result
 finally:
  (out/'capture.log').write_text('\n'.join(log))
  if s.g:s.g.p.kill()
  try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except (ProcessLookupError,FileNotFoundError):pass
