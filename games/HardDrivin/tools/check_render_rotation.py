"""Native/model/replacement comparison, including overflow, overlap and full CCR."""
from pathlib import Path
import os,sys,subprocess,struct,json,hashlib,random
exec(Path('tools/check_sweep_native.py').read_text().split('import subprocess,sys')[0])
sys.path.insert(0,'tools');from game_image import hunks
src=Path('src/HardDrivinRotation.s').read_text();body=src[src.index('_render_rotate_y:'):]
p=Path('tmp/s5-rotation-contract');p.with_suffix('.s').write_text(' org $400100\n jmp _render_rotate_y\n jmp _render_rotate_x\n'+body)
subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
write(0x400100,p.with_suffix('.bin').read_bytes());write(0x100000,hunks()[0]['data']);write(0x490000,bytes.fromhex('40f900470000'));rng=random.Random(5405);ncase=0

def signed(x):return x-65536 if x&32768 else x

def model(buf,offset,count,cos,sin,axis):
 b=bytearray(buf);si=256;di=offset
 def get(o):return struct.unpack_from('>h',b,o)[0]
 def put(o,v):struct.pack_into('>H',b,o,v&65535)
 for _ in range(max(0,count)):
  if axis=='x':put(di,get(si));si+=2;di+=2;a,z=get(si),get(si+2);si+=4
  else:a,y,z=get(si),get(si+2),get(si+4);si+=6
  v=((a*cos-z*sin)&0xffffffff)>>14;w=((z*cos+a*sin)&0xffffffff)>>14
  put(di,v);di+=2
  if axis=='y':put(di,y);di+=2
  put(di,w);di+=2
 return bytes(b)
for axis,entry,original in [('y',0x400100,0x102a2e),('x',0x400106,0x102a7a)]:
 for i in range(3000):
  count=rng.choice([-1,0,1,2,3,6,26,67]);cos,sin=rng.choice([(0,0),(0,16384),(0,-16384),(16384,0),(-16384,0),(0,rng.randrange(-32768,32768)),(rng.randrange(-32768,32768),0),(rng.randrange(-32768,32768),rng.randrange(-32768,32768))]);dst=rng.choice([128,250,254,256,258,262,1024]);buf=rng.randbytes(2048);registers=[rng.getrandbits(32) for _ in range(16)];ccr=rng.randrange(32);results=[]
  for pc in [original,entry]:
   write(0x350000,buf)
   for k,v in enumerate(registers,1):reg(k,v)
   reg(17,0x2000|ccr);reg(8,0x4fff00);pack(0x4fff00,'IhhhII',0x490000,count,cos,sin,0x350000+dst,0x350100)
   ok(u.uc_emu_start(h,pc,0x490000,1000000,100000));ok(u.uc_emu_start(h,0x490000,0x490006,1000000,1))
   results.append((read(0x350000,2048),[reg(k) for k in range(1,17)],read(0x470000,2)))
  assert results[0]==results[1],(axis,i,count,cos,sin,dst,'native/asm',results[0][1:],results[1][1:])
  assert results[0][0]==model(buf,dst,count,cos,sin,axis),(axis,i,count,cos,sin,dst,'model')
  ncase+=1
r=dict(passed=True,cases=ncase,source_sha256=hashlib.sha256(src.encode()).hexdigest(),scope='Native original/Python model/assembled replacement; random signed words, zero coefficients, arithmetic wrap, negative/zero counts, overlapping buffers; full guarded memory, registers, stack, CCR including X.')
Path('tmp/s5-rotation-contract.json').write_text(json.dumps(r,indent=2)+'\n');print(r);ok(u.uc_close(h))
