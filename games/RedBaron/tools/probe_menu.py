#!/usr/bin/env python3
"""Boot an isolated VERIFY build with a fixed menu-only keyboard sequence."""
import argparse,json,os,shutil,subprocess,sys,time
from pathlib import Path
import route_status as r
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev.env import path
p=argparse.ArgumentParser();p.add_argument('keys',help='Comma-separated enter/tab/right/left/up/down/esc');p.add_argument('--out',required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[1];os.chdir(root)
keys=dict(enter=0x440d,tab=0x4209,right=0x4e00,left=0x4f00,up=0x4c00,down=0x4d00,esc=0x451b)
sequence=[keys[k] for k in a.keys.split(',')]
out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
if (root/'tmp/run/default/.run/redbaron.sock').exists():r.command('quit')
src=root/'tmp/build/menu-probe-source';shutil.copytree(root.parent.parent/'src',src,dirs_exist_ok=True)
(src/'tape-route.i').write_text('tape_dense:\n'+''.join(f' dc.w 100,${k:04x}\n' for k in sequence)+' dc.w 0\n')
whd=Path(path('WHDLOAD'));slave=out/'slave.slave'
subprocess.run([path('VASM'),'-DVERIFY=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+str(Path(path('AMIGA_SHARE'))/'include'),'-I'+str(whd/'Include'),'-I'+str(whd/'Src/sources'),'-I'+str(Path(path('AMIGA_SHARE'))/'ndk/Include_I'),'-L',str(out/'slave.lst'),'-o',str(slave),'RedBaronHD.s'],cwd=src,check=True)
env=dict(os.environ,SLAVE=str(slave),WARP='1',DETERMINISTIC='1',JOY0='none',JOY0_MODE='nothing',JOY1='none')
with (out/'serve.log').open('w') as log:server=subprocess.Popen([sys.executable,'tools/redbaron.py','serve'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
deadline=time.monotonic()+120
while time.monotonic()<deadline:
 try:
  if server.poll() is not None:raise SystemExit('server exited')
  at=r.locate();state=r.read(at)
  if state['events']>=len(sequence):break
 except (ConnectionRefusedError,FileNotFoundError,RuntimeError):pass
 time.sleep(.5)
else:raise SystemExit('menu route timeout')
r.command('wait 2');r.command('stop');state=r.read(at)
print(json.dumps(state,indent=2));(out/'state.json').write_text(json.dumps(state,indent=2))
print(r.command('shot '+str(out/'screen.png')))
