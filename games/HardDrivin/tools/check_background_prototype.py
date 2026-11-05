from pathlib import Path
import os,sys,subprocess,struct,json,random,hashlib
exec(Path('tools/check_sweep_native.py').read_text().split('import subprocess,sys')[0])
sys.path.insert(0,'tools');from game_image import hunks
src=Path('tmp/s5-background-prototype.s').read_text();macro=(Path(os.environ['WHDLOAD'])/'Include/whdmacros.i').read_text().split('BLITWAIT MACRO',1)[1].split('ENDM',1)[0]
p=Path('tmp/s5-background-contract');p.with_suffix('.s').write_text(' org $400100\nBLITWAIT MACRO'+macro+'ENDM\n_custom equ $dff000\n_ciaa equ $bfe001\ndmaconr equ 2\nDMAB_BLTDONE equ 14\n'+src)
subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
write(0x400100,p.with_suffix('.bin').read_bytes());write(0x100000,hunks()[0]['data']);write(0x490000,bytes.fromhex('40f900470000'));ok(u.uc_mem_map(h,0xdff000,0x1000,7));ok(u.uc_mem_map(h,0xbfe000,0x1000,7))
cbtype=C.CFUNCTYPE(None,P,I,U,I,C.c_int64,P)
@cbtype
def onwrite(uc,kind,addr,size,value,userdata):
 if addr!=0xdff058:return
 con=struct.unpack('>H',read(0xdff040,2))[0];dest=struct.unpack('>I',read(0xdff054,4))[0];assert con in [0x100,0x1ff]
 assert struct.unpack('>H',read(0xdff066,2))[0]==0
 width=value&63;height=value>>6;write(dest,bytes([255 if con==0x1ff else 0])*(width*2*height))
u.uc_hook_add.argtypes=[P,C.POINTER(Z),I,P,P,U,U];u.uc_hook_add.restype=I;hook=Z();ok(u.uc_hook_add(h,C.byref(hook),1<<11,C.cast(onwrite,P),None,0xdff058,0xdff058))
rng=random.Random(5505);cases=0
for n in range(1200):
 top=rng.randrange(0,100);bottom=rng.randrange(top,135);lo=rng.randrange(-30,200);hi=rng.randrange(-30,200);yoff=rng.randrange(0,65);patterns=[rng.choice([0,0xffffffff,rng.getrandbits(32)]) for _ in range(4)];buf=rng.randbytes(34000);regs=[rng.getrandbits(32) for _ in range(16)];ccr=rng.randrange(32);results=[]
 for pc in [0x103a28,0x400100]:
  write(0x350000,buf);pack(0x300000,'4I',*patterns)
  for k,v in enumerate(regs,1):reg(k,v)
  reg(17,0x2000|ccr);reg(5,0x280000);reg(8,0x4fff00);pack(0x4fff00,'Ihh',0x490000,lo,hi)
  for off,fmt,v in [(0x69f2,'h',top),(0x69f4,'h',bottom),(0x69e6,'h',yoff),(0x69f6,'h',40),(0x6a12,'I',0x350200),(0x69e4,'I',0x300000)]:pack(0x280000-off,fmt,v)
  ok(u.uc_emu_start(h,pc,0x490000,1000000,100000));ok(u.uc_emu_start(h,0x490000,0x490006,1000000,1));results.append((read(0x350000,len(buf)),[reg(k) for k in range(1,17)],read(0x470000,2)))
 assert results[0]==results[1],(n,lo,hi,top,bottom,yoff,patterns,results[0][1:],results[1][1:])
 expected=bytearray(buf)
 for plane,pattern in enumerate(patterns):
  for y in range(max(lo,top),min(hi,bottom)+1):
   word=(pattern&65535) if (y-max(lo,top))%2==0 else pattern>>16;start=0x200+plane*8000+(y+yoff)*40;expected[start:start+40]=struct.pack('>H',word)*20
 assert results[0][0]==bytes(expected),(n,'model');cases+=1
r=dict(passed=True,cases=cases,source_sha256=hashlib.sha256(src.encode()).hexdigest(),scope='Native/Python/assembled contract; four guarded planes, clip boundaries, patterned fallback, all registers/stack/CCR. Blitter stores are modeled, hardware timing/pixels require emulator validation.');Path('tmp/s5-background-contract.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
