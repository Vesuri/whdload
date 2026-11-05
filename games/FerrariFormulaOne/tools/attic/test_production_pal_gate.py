from pathlib import Path
import os,sys,json,signal,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);out=r/'tmp/step5/production-pal-gate';out.mkdir(exist_ok=True)
b=r/'tmp/build/production/FerrariFormulaOne.slave';build=json.loads((b.parent/'build.json').read_text());hs=build['host_symbols'];host=int(json.loads((r/'tmp/step5/c4-q03-production-timing-a500-candidate/result.json').read_text())['host'],16)
os.environ.update(json.loads((r/'manifest/step3-profiles.json').read_text())['a500']);os.environ.update(SLAVE=str(b),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',NTSC='1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae-q03-final'))
s=Server('ff1measure',root=str(r),profile_window=False);log=[]
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=90);log.append(c+'\n'+v);return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 cmd(f'break *{host+hs["FF1RequirePAL"]}');assert 'Breakpoint' in cmd('continue')
 assert val('$pc')==host+hs['FF1RequirePAL'];monitor=val(f'*(unsigned int*){host+hs["FF1ProfileMonitor"]}');assert monitor!=0x21000
 cmd('stepi');reason=val('*(unsigned int*)$sp');assert reason==14
 report={'status':'passed','slave_sha256':hashlib.sha256(b.read_bytes()).hexdigest(),'monitor':hex(monitor),'abort_reason':reason,'scope':'Actual NTSC startup of unmodified production reaches PAL rejection before public loader activation.'}
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
