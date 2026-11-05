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
b=0x10000;a4=0x30000;a5=0x38000;sp=0x4fff0;native=0x2b754;stop=0x20000
sy={n:b+int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',Path('tmp/force-cache-micro.lst').read_text(),re.M)}
write(b,Path('tmp/force-cache-micro.bin').read_bytes());rng=random.Random(547);st=sy['_drivetrain_force_state'];last=None;cached=None;hits=misses=bypasses=0
key=[0,0,0,0,0,0]
try:
 for i in range(2400):
  if i%4==0:
   j=(i//4)%6;key[j]=rng.randrange(65536 if j<4 else 256)
  active=1 if i%13 else rng.choice([0,2]);road=0 if i%17==0 else rng.choice([1,255])
  pack(sy['_drivetrain_state']+6,'H',active)
  for off,v in zip([0x9928,0xf790,0x944c],[key[0],key[2],key[3]]):pack(a4+off-65536,'H',v)
  pack(a4+0x9911-65536,'B',key[4]);pack(a4+0xaf31-65536,'B',key[5]);pack(a4+0xe94a-65536,'B',road)
  write(a5-20,bytes([0xa5])*20);pack(a5-14,'H',key[1]);before=read(a5-20,20)
  reg(17,0x2000)
  for k in range(1,17):reg(k,k*0x10101)
  reg(5,a4);reg(6,a5);reg(8,sp);reg(13,0xabcd8123);pack(sp,'I',native);saved=[reg(k) for k in range(1,17)]
  eligible=active==1 and road!=0;hit=eligible and tuple(key)==last
  target=0x2b8a2 if hit else native if key[0]&0x8000 else native+4
  ok(u.uc_emu_start(h,b,target,1000000,3000));assert reg(18)==target and reg(8)==sp+4
  assert all(reg(k)==saved[k-1] for k in range(1,17) if k not in (8,13))
  if hit:
   assert [struct.unpack('>H',read(a5+off,2))[0] for off in [-2,-4,-6,-8,-18]]==cached[:5]
   assert reg(13)==0xabcd0000|cached[5];hits+=1
  else:
   assert read(a5-20,20)==before and reg(13)==saved[12]
   misses+=eligible;bypasses+=not eligible
  assert struct.unpack('>H',read(st+2,2))[0]==int(eligible and not hit)
  # Simulate only the native force outputs, then invoke the actual save helper.
  outputs=[rng.randrange(65536) for _ in range(6)]
  for off,v in zip([-2,-4,-6,-8,-18],outputs):pack(a5+off,'H',v)
  reg(13,0xabcd0000|outputs[5]);reg(8,sp);pack(sp,'I',stop);save_regs=[reg(k) for k in range(1,17)]
  ok(u.uc_emu_start(h,sy['_drivetrain_force_save'],stop,1000000,1000))
  assert reg(8)==sp+4 and all(reg(k)==save_regs[k-1] for k in range(1,17) if k!=8)
  if eligible and not hit:last=tuple(key);cached=outputs
  assert struct.unpack('>2I',read(st+4,8))==(hits,misses) and struct.unpack('>H',read(st+2,2))[0]==0
 result=dict(passed=True,actual_68000_enter_save_pairs=2400,hits=hits,misses=misses,bypasses=bypasses,all_six_key_components_exercised=True,locals_registers_and_stack=True)
 Path('tmp/force-cache-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:ok(u.uc_close(h))
