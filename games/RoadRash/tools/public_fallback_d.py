import os,sys,subprocess,shutil,json
from pathlib import Path
from matrix_a import config,cleanup
root=Path.cwd();os.environ['FSUAE']=str(root/'tmp/b-gdb-passive-emulator/fs-uae')
s=(root/'tools/check_a.py').read_text().replace("        end=snapshot(s);", "        assert rd(s,0x80000,2)!=0x4ef9, 'unexpected public entry trampoline'\n        end=snapshot(s);")
(root/'tools/check_fallback_d.py').write_text(s)
for i,kind in enumerate(['no-allocation','odd-relocation']):
 src=root/f'tmp/d-public-{kind}-source';shutil.copytree(root/'src',src)
 if kind=='no-allocation':
  p=src/'RoadRashHD.s';p.write_text(p.read_text().replace('dc.l -$50000 ; optional public main image, stack and reserved headroom','dc.l 0 ; diagnostic unavailable expansion memory'))
 else:
  p=src/'public_main.s';p.write_text(p.read_text().replace(' movem.l d0-d7/a0-a6,-(a7)',' movem.l d0-d7/a0-a6,-(a7)\n move.l #1,$bc418 ; diagnostic corrupt relocation offset',1))
 build=root/f'tmp/d-public-{kind}-build';subprocess.run(['bash','tools/build.sh'],env=dict(os.environ,RR_SOURCE=str(src),RR_BUILD_OUT=str(build)),check=True,stdout=subprocess.DEVNULL)
 out=root/f'tmp/d-public-{kind}';out.mkdir();env=config('a1200-fast');env.update(SLAVE=str(build/'RoadRash.slave'),WHD_ARGS='CUSTOM2=1',DEBUG_PORT=str(27484+i))
 try:
  with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/check_fallback_d.py',str(out),'--normal'],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=180)
 finally:cleanup(out)
 print(kind,p.returncode,flush=True);assert not p.returncode
