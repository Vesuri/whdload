from pathlib import Path
exec(Path('tools/check_record_equal_micro.py').read_text().split('for addr,name in ')[0])
import subprocess
from game_image import hunks
source=Path('src/HardDrivinRecord.s').read_text();body=source[source.index('.capture:'):source.index('\n\tlea _record_state(pc),a3',source.index('.capture:'))]
stem=Path('tmp/p2-sampler');stem.with_suffix('.s').write_text(' org $11000\n'+body+'\n rts\n_record_current_ptr: dc.l $28000\n');subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);write(0x11000,stem.with_suffix('.bin').read_bytes());write(0x10000,hunks()[0]['data'][0x89d8:0x8a9c]);sp=0x4fff0;ret=0x18000;a4=0x40000;dest=0x28000;rng=random.Random(89)
for case in range(4000):
 count=rng.choice([12,12,12,rng.randrange(13)])
 for off in [0x98f0,0x98f2,0x98f4,0x9944,0x9946,0x9948,0x9602]:pack(a4+off-65536,'H',rng.randrange(65536))
 write(a4-0x50cf,bytes([rng.randrange(256)]));pack(a4-0x50fc,'H',count);pack(a4-0x50fa,'I',0x20000)
 for j in range(12):pack(0x20000+j*46+8,'I',0x24000+j*32);write(0x24000+j*32,bytes(rng.randrange(256) for _ in range(32)))
 initial=bytes(rng.randrange(256) for _ in range(158));outputs=[]
 for entry in [0x10000,0x11000]:
  write(dest-4,b'X'*166);write(dest,initial);pack(a4-0x16e2,'I',dest);reg(17,0x2000);reg(5,a4);reg(8,sp);pack(sp,'I',ret);ok(u.uc_emu_start(h,entry,ret,1000000,2000));assert reg(8)==sp+4;assert read(dest-4,4)==read(dest+158,4)==b'XXXX';outputs.append(read(dest,158))
 assert outputs[0]==outputs[1],(case,count)
report=dict(passed=True,actual_68000_native_sampler_pairs=4000,traffic_counts='0..12; unrolled 12-car path and generic fallback',guard_bytes=True);Path('tmp/p2-sampler.json').write_text(json.dumps(report,indent=2)+'\n');print(report);ok(u.uc_close(h))
