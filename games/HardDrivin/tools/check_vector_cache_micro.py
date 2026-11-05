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
sy={n:b+int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',Path('tmp/vector-cache-micro.lst').read_text(),re.M)}
write(b,Path('tmp/vector-cache-micro.bin').read_bytes());st=sy['_drivetrain_vector_state'];rng=random.Random(181);cases=hits=misses=0
word=lambda v:(v+32768)%65536-32768
try:
 for group in range(120):
  active=[0,1,1,1,2][group%5];pack(sy['_drivetrain_state']+6,'H',active)
  write(st,bytes(44));keys=[None,None];victim=0;gh=gm=0
  trig=[rng.randint(-32768,32767) for _ in range(4)] if group%4==0 else [rng.randint(-16384,16384) for _ in range(4)]
  for off,v in zip([0x9448,0x944a,0x944c,0x944e],trig):pack(a4+off-65536,'h',v)
  velocity=rng.randint(-32768,32767)
  for step in range(32):
   velocity=word(velocity+rng.choice([0,0,0,1,-1,300]));input_long=(rng.getrandbits(16)<<16)|(velocity&65535)
   speed=word((velocity>>1)+velocity);along=word((speed*trig[3])>>14)
   expected=[(along*trig[0])>>14,(speed*trig[2])>>14,(along*trig[1])>>14]
   carry=((along*trig[1])>>13)&1;flags=(17 if carry else 0)+(4 if expected[2]==0 else 8 if expected[2]<0 else 0)
   reg(17,0x2000)
   for k in range(1,17):reg(k,k*0x10101)
   reg(5,a4);reg(8,sp);reg(9,input_long);pack(sp,'I',end);saved=[reg(k) for k in range(1,17)]
   ok(u.uc_emu_start(h,b,end,1000000,2000))
   assert [reg(k) for k in [9,10,11]]==[v&0xffffffff for v in expected],(group,step)
   assert reg(13)==14 and (reg(17)&31)==flags,(group,step,reg(17)&31,flags)
   assert all(reg(k)==saved[k-1] for k in [1,2,3,4,5,6,7,12,14,15,16]) and reg(8)==sp+4
   if active==1:
    if velocity in keys:gh+=1
    else:gm+=1;keys[victim]=velocity;victim^=1
   assert struct.unpack('>2I',read(st,8))==(gh,gm)
   cases+=1
  hits+=gh;misses+=gm
 result=dict(passed=True,actual_68000_cases=cases,hits=hits,misses=misses,full_long_results_flags_registers_stack=True,outer_reset_groups=120)
 Path('tmp/vector-cache-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:ok(u.uc_close(h))
