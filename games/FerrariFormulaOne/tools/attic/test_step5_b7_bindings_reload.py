from pathlib import Path
import os,sys,json,signal,hashlib,re,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);b=r/'tmp/build/step5-b7-bindings-reload-test';listing=(b/'binding.list').read_text();profiles=json.loads((r/'manifest/step3-profiles.json').read_text());expected=json.loads((b/'expected.json').read_text());kick=os.environ['KICKSTART']
def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M)[1],16)
for profile in ('a1200-fast','a500'):
 out=r/f'tmp/step5/b7-bindings-reload-{profile}';out.mkdir(parents=True,exist_ok=True)
 os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b/'binding.slave'),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else kick)
 s=Server('ff1measure',root=str(r),profile_window=False);log=[]
 try:
  g=s.boot()
  def cmd(c):
   v=g.cmd(c,timeout=180);log.append(c+'\n'+v);return v
  def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
  cmd('break *0x65174');assert 'Breakpoint' in cmd('continue')
  probe=val('*(unsigned int*)0x654e8')-sym('barrier');at=probe+sym('results');cmd(f'dump binary memory {out.relative_to(r)}/results.bin {at} {at+len(expected)*8}')
  data=(out/'results.bin').read_bytes();cases=[dict(name=e['name'],expected=e['expect'],actual=list(struct.unpack_from('>HHI',data,i*8))) for i,e in enumerate(expected)];passed=all(x['expected']==x['actual'] for x in cases)
  report=dict(profile=profile,status='passed' if passed else 'failed',cases=cases,slave_sha256=hashlib.sha256((b/'binding.slave').read_bytes()).hexdigest());(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(profile,report['status'],[x for x in cases if x['expected']!=x['actual']],flush=True);assert passed
 finally:
  (out/'capture.log').write_text('\n'.join(log))
  if s.g:s.g.p.kill()
  try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except (ProcessLookupError,FileNotFoundError):pass
