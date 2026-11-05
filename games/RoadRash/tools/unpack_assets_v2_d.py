from pathlib import Path
import shutil,os,sys,subprocess,json
from matrix_a import config,cleanup
root=Path.cwd();src=root/'tmp/d-unpack-assets-v2-source';shutil.copytree(root/'src',src)
files=sorted((root/'tmp/game/RoadRash/data').iterdir(),key=lambda p:p.name.lower())
p=src/'RoadRashHD.s';s=p.read_text().replace('\t\t;get password','\t\tbra public_unpack_audit\n\t\t;get password',1)
s+='''
public_unpack_audit:
 lea public_unpack_names(pc),a3
 moveq #0,d7
.next:
 move.l (a3)+,d0
 bmi .done
 lea _base(pc),a0
 adda.l d0,a0
 lea $20000,a1
 move.l _resload(pc),a2
 jsr (resload_LoadFileDecrunch,a2)
 movem.l a2-a6,-(a7)
 lea $20000,a0
 bsr public_unpack_ice
 movem.l (a7)+,a2-a6
 move.l d0,d6
 move.l (a3)+,d0
 lea _base(pc),a0
 adda.l d0,a0
 move.l d6,d0
 lea $20000,a1
 jsr (resload_SaveFile,a2)
 addq.l #1,d7
 bra .next
.done:
 pea TDREASON_OK
 jsr (resload_Abort,a2)
public_unpack_names:
'''
for i,p in enumerate(files):s+=f' dc.l public_unpack_in_{i}-_base,public_unpack_out_{i}-_base\n'
s+=' dc.l -1\n'
for i,p in enumerate(files):s+=f'public_unpack_in_{i}: dc.b "{p.name}",0\npublic_unpack_out_{i}: dc.b "_audit_{i:02d}.bin",0\n'
s+=' even\npublic_unpack_ice:\n incbin ice-audit.bin\n';(src/'ice-audit.bin').write_bytes((root/'tmp/game/RoadRash/data/lomain.ami').read_bytes()[0x50ea:0x52e6]);(src/'RoadRashHD.s').write_text(s);(root/'tmp/d-unpack-assets-files.json').write_text(json.dumps([p.name for p in files],indent=2)+'\n')
build=root/'tmp/d-unpack-assets-v2-build';subprocess.run(['bash','tools/build.sh'],env=dict(os.environ,RR_SOURCE=str(src),RR_BUILD_OUT=str(build)),check=True,stdout=subprocess.DEVNULL)
env=config('040-25');env.update(FSUAE=str(root/'tmp/b-gdb-passive-emulator/fs-uae'),SLAVE=str(build/'RoadRash.slave'),DEBUG_PORT='27612',WHD_ARGS='CUSTOM2=0');out=root/'tmp/d-unpack-assets-v2';out.mkdir()
try:
 with (out/'run.log').open('w') as log:p=subprocess.run([sys.executable,'tools/unpack_assets_probe_d.py',str(out)],env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
finally:cleanup(out)
print(p.returncode)
