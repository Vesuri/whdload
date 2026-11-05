from pathlib import Path
import os,sys,json,signal,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profiles=json.loads((r/'manifest/step3-profiles.json').read_text());kick=os.environ['KICKSTART'];option=int(os.environ.get('RELEASE_CUSTOM1','1'));report={'scope':'CUSTOM2=0 versus unchanged release, both with step-1 RNG/countdown control; identical slave size and WHDLoad reservation. Three matched loops, unchanged 26-block exact-state inventory.','profiles':{}}
blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[dict(name='gear',address='0x6bf84',bytes=4),dict(name='instrument_phase',address='0x6c942',bytes=6),dict(name='instrument_rates',address='0x66c88',bytes=4),dict(name='flag_counter',address='0x66be0',bytes=2)]
previous=r/f'manifest/render-h10-default-c{option}-validation.json'
if previous.exists(): report['profiles'].update(json.loads(previous.read_text()).get('profiles',{}))
for profile in os.environ.get('RELEASE_PROFILES','a500,a500-fast,a1200,a1200-fast').split(','):
 for arm in ('release','production'):
  out=r/f'tmp/step5/render-h10-default-c{option}-{profile}-{arm}';out.mkdir(exist_ok=True);b=r/('tmp/build/render-h10-default-c1-control' if option else 'tmp/build/render-h10-default-control')/f'{arm}-{"020" if profile.startswith("a1200") else "000"}.slave'
  os.environ.update(profiles[profile]);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',WHD_ARGS=f'CUSTOM1={option} CUSTOM2=0 ConfigDelay=0',DETERMINISTIC='1',FSUAE=str(r/'tmp/step5-frame-observer-build/fs-uae'),FF1_FRAME_SENTINEL='0',KICKSTART=os.environ['KICKSTART_A1200'] if profile.startswith('a1200') else kick)
  s=Server('ff1measure',root=str(r),run_script=os.environ.get('RELEASE_RUN_SCRIPT','amiga/run.sh'),profile_window=False);log=[]
  try:
   g=s.boot()
   def cmd(c):
    v=g.cmd(c,timeout=180);log.append(c+'\n'+v);return v
   cmd('break *0x65174');cmd('ignore $bpnum 124');assert 'Breakpoint' in cmd('continue');cmd('monitor warp 0')
   for tick in (125,150,175):
    if tick!=125:cmd('ignore $bpnum 24');assert 'Breakpoint' in cmd('continue')
    cmd(f'dump binary memory {out.relative_to(r)}/loop{tick}.bin 0 0x80000')
   (out/'result.json').write_text(json.dumps(dict(status='passed',slave_sha256=hashlib.sha256(b.read_bytes()).hexdigest()),indent=2))
   print(profile,arm,'captured',flush=True)
  except Exception as error:
   try:
    g.stop();s.handle(g,'shot '+str(out/'failure.png'));log.append(g.cmd('info registers'))
   except Exception:pass
   raise
  finally:
   (out/'capture.log').write_text('\n'.join(log))
   if s.g:s.g.p.kill()
   try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
   except (ProcessLookupError,FileNotFoundError):pass
 bad=[]
 for tick in (125,150,175):
  a=(r/f'tmp/step5/render-h10-default-c{option}-{profile}-release/loop{tick}.bin').read_bytes();b=(r/f'tmp/step5/render-h10-default-c{option}-{profile}-production/loop{tick}.bin').read_bytes()
  for block in blocks:
   at=int(block['address'],16);n=block['bytes']
   if a[at:at+n]!=b[at:at+n]:bad.append((tick,block['name']))
 report['profiles'][profile]=dict(passed=not bad,failures=bad,config_delay=0,runtime_sha256=hashlib.sha256(Path(os.environ['WHDLOAD_BINARY']).read_bytes()).hexdigest());print(profile,report['profiles'][profile],flush=True)
 (r/f'manifest/render-h10-default-c{option}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 assert not bad,bad
report['status']='passed';(r/f'manifest/render-h10-default-c{option}-validation.json').write_text(json.dumps(report,indent=2)+'\n')
