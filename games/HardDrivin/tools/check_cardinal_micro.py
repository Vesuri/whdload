import ctypes as C,json,os,random,re,struct
from pathlib import Path
u=C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.dylib'))
P=C.c_void_p; U=C.c_uint64; Z=C.c_size_t; I=C.c_int
for name,args in [('uc_open',[I,I,C.POINTER(P)]),('uc_ctl',[P,C.c_uint32]),('uc_mem_map',[P,U,Z,C.c_uint32]),('uc_mem_write',[P,U,P,Z]),('uc_mem_read',[P,U,P,Z]),('uc_reg_write',[P,I,P]),('uc_reg_read',[P,I,P]),('uc_emu_start',[P,U,U,U,Z]),('uc_close',[P])]:
 f=getattr(u,name);f.argtypes=args;f.restype=I
u.uc_strerror.argtypes=[I];u.uc_strerror.restype=C.c_char_p
def ok(x):assert x==0,u.uc_strerror(x)
h=P();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,0x44000007,I(1)));ok(u.uc_mem_map(h,0x10000,0x40000,7))
def write(a,b):ok(u.uc_mem_write(h,a,b,len(b)))
def read(a,n):b=C.create_string_buffer(n);ok(u.uc_mem_read(h,a,b,n));return b.raw
def reg(k,v=None):
 x=C.c_uint32(v or 0)
 if v is None:ok(u.uc_reg_read(h,k,C.byref(x)));return x.value
 ok(u.uc_reg_write(h,k,C.byref(x)))
def pack(a,fmt,*v):write(a,struct.pack('>'+fmt,*v))
def trunc(x):return abs(x)//65536*(-1 if x<0 else 1)
b=0x10000;a4=0x30000;sp=0x4fff0;end=0x20000
write(b,Path('tmp/cardinal-micro.bin').read_bytes());write(end,bytes.fromhex('40f9000200104e71'));rng=random.Random(245);cases=fast=0
word=lambda v:(v+32768)%65536-32768
trigs=[(16384,0,0,16384),(-16384,0,0,16384),(0,16384,0,16384),(0,-16384,0,16384)]
trigs += [(a,b,c,d) for a,b,c,d in [(16383,0,0,16384),(16384,1,0,16384),(16384,0,1,16384),(16384,0,0,16383)]]
trigs += [tuple(rng.randint(-32768,32767) for _ in range(4)) for i in range(40)]
velocities=[-32768,-21845,-21844,-21843,-1,0,1,21843,21844,21845,32767]+[rng.randint(-32768,32767) for _ in range(89)]
try:
 for trig in trigs:
  for off,v in zip([0x9448,0x944a,0x944c,0x944e],trig):pack(a4+off-65536,'h',v)
  for velocity in velocities:
   speed=word((velocity>>1)+velocity);along=word((speed*trig[3])>>14);expected=[(along*trig[0])>>14,(speed*trig[2])>>14,(along*trig[1])>>14]
   carry=((along*trig[1])>>13)&1;flags=(17 if carry else 0)+(4 if expected[2]==0 else 8 if expected[2]<0 else 0)
   reg(17,0x2000|rng.randrange(32))
   for k in range(1,17):reg(k,k*0x10101)
   reg(5,a4);reg(8,sp);reg(9,(rng.getrandbits(16)<<16)|(velocity&65535));pack(sp,'I',end);saved=[reg(k) for k in range(1,17)]
   ok(u.uc_emu_start(h,b,end+8,1000000,2000))
   assert [reg(k) for k in [9,10,11]]==[v&0xffffffff for v in expected],(trig,velocity)
   assert reg(13)==14 and (struct.unpack('>H',read(end+16,2))[0]&31)==flags,(trig,velocity,reg(17)&31,flags)
   assert all(reg(k)==saved[k-1] for k in [1,2,3,4,5,6,7,12,14,15,16]) and reg(8)==sp+4
   cases+=1;fast+=trig in trigs[:4]
 result=dict(passed=True,actual_68000_cases=cases,cardinal_cases=fast,general_cases=cases-fast,full_long_results_flags_registers_stack=True)
 Path('tmp/cardinal-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:ok(u.uc_close(h))
