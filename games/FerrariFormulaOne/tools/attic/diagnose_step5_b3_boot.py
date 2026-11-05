from pathlib import Path
import os,sys,signal,json
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];os.chdir(r);out=r/'tmp/step5/a1200-b3-control-boot-diagnostic';out.mkdir(parents=True,exist_ok=True)
os.environ.update(CPU='68EC020',AMIGA_MODEL='A1200',CHIP_KB='2048',SLOW_KB='0',FAST_KB='0',KICKSTART=os.environ['KICKSTART_A1200'],SLAVE=str(r/'tmp/build/step5-b3-native-control/fine.slave'),WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1 CUSTOM2=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'))
s=Server('ff1measure',root=str(r),profile_window=False)
try:
 g=s.boot();g.cmd('break *0x65174')
 try:v=g.cmd('continue',timeout=30)
 except TimeoutError:
  os.kill(g.p.pid,signal.SIGINT);v=g.read_until(g.sent,30)
 (out/'state.json').write_text(json.dumps({'response':v,'registers':g.cmd('info registers')},indent=2))
 g.cmd(f'monitor profile 1 "" "{out}/screen.bin"',timeout=60);(out/'screen.png').write_bytes(barto.load(out/'screen.bin').fields[-1].shot)
 print(v[-300:])
finally:
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
