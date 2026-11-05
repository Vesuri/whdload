from pathlib import Path
import os,sys,json,signal,hashlib,re,struct
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);b=r/'tmp/build/step5-b8-pose-test';listing=(b/'pose.list').read_text();profiles=json.loads((r/'manifest/step3-profiles.json').read_text());expected=json.loads((b/'expected.json').read_text());kick=os.environ['KICKSTART']
def sym(n):return int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)',listing,re.M)[1],16)
for profile in ('a1200-fast',):
 out=r/f'tmp/step5/b8-pose-{profile}';out.mkdir(parents=True,exist_ok=True)
 os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b/'pose.slave'),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else kick)
 s=Server('ff1measure',root=str(r),profile_window=False);log=[]
 try:
  g=s.boot()
  def cmd(c):
   v=g.cmd(c,timeout=180);log.append(c+'\n'+v);return v
  def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
  cmd('break *0x65174');assert 'Breakpoint' in cmd('continue')
  probe=val('*(unsigned int*)0x654e8')-sym('barrier');at=probe+sym('results');cmd(f'dump binary memory {out.relative_to(r)}/results.bin {at} {at+len(expected)*16}')
  at=probe+sym('inputs');cmd(f'dump binary memory {out.relative_to(r)}/inputs-after.bin {at} {at+len(expected)*28}')
  assert (out/'inputs-after.bin').read_bytes()==(b/'inputs.bin').read_bytes(), 'Source poses were modified'
  data=(out/'results.bin').read_bytes();bad=[]
  for i,e in enumerate(expected):
   actual=list(struct.unpack_from('>6hI',data,i*16));want=e['expected']+[e['ret']]
   if actual!=want:bad.append(dict(index=i,case=e,actual=actual))
  report=dict(profile=profile,status='passed' if not bad else 'failed',cases=len(expected),failures=bad,slave_sha256=hashlib.sha256((b/'pose.slave').read_bytes()).hexdigest());(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(bad),bad[:3],flush=True);assert not bad

 finally:
  (out/'capture.log').write_text('\n'.join(log))
  if s.g:s.g.p.kill()
  try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
  except (ProcessLookupError,FileNotFoundError):pass
