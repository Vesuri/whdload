from pathlib import Path
import os,sys,signal,json
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r)
os.environ.update(json.loads((r/'manifest/step3-profiles.json').read_text())['a1200'])
os.environ.update(SLAVE=str(r/'tmp/build/step5-verify-split-v3/verify/fine.slave'),KICKSTART=os.environ['KICKSTART_A1200'],WARP='1',WINDOW='none',WHD_ARGS='CUSTOM1=1',DETERMINISTIC='1',FSUAE=str(r/'tmp/step3/fs-uae'))
o=r/'tmp/step5/s2-verify-startup-diagnosis';o.mkdir(exist_ok=True)
s=Server('ff1measure',root=str(r),profile_window=False)
try:
 g=s.boot();g.cmd('break *0x6a304')
 try:v=g.cmd('continue',timeout=40)
 except TimeoutError:
  g.p.send_signal(signal.SIGINT);v=g.read_until(g.sent,60)
 print(v[-1200:],flush=True)
 (o/'registers.txt').write_text(g.cmd('info registers'))
 g.cmd(f'dump binary memory {o}/memory.bin 0 0x200000')
 g.cmd('delete');g.cmd(f'monitor profile 1 "" "{o}/detail.bin"',timeout=60)
 from amigaxdev import barto
 kind,data=barto.last_screenshot(o/'detail.bin');print('screenshot',kind,len(data),flush=True)
 (o/('screenshot.'+('png' if data[:4]==b'\x89PNG' else 'jpg'))).write_bytes(data)
finally:
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
