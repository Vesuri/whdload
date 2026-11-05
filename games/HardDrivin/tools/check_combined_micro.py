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
b=0x10000;a4=0x30000;ret=0x18000;sp=0x4fff0
sy={n:b+int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',Path('tmp/position-combined-micro.lst').read_text(),re.M)}
write(b,Path('tmp/position-combined-micro.bin').read_bytes())
r=random.Random(481);fast=fall=0
try:
 for case in range(3000):
  n=1 if case<2500 else r.choice([0,1,2,8,9,65535]);lim=16383 if case<2000 else 32768
  v=[r.choice([-lim,-1,0,1,lim]) if case%2 else r.randint(-lim,lim) for _ in range(3)]
  prev=[r.choice([-lim,-1,0,1,lim]) if case%2 else r.randint(-lim,lim) for _ in range(3)]
  v=[min(x,32767) for x in v];prev=[min(x,32767) for x in prev]
  q=[r.choice([-114688,-1,0,1,114688]) for _ in range(3)];pq=[r.choice([-114688,-1,0,1,114688]) for _ in range(3)]
  ic=[r.choice([-127,0,127]) for _ in range(3)];fine=[r.choice([-65535,0,65535]) for _ in range(3)];pos=[r.randint(-1000000,1000000) for _ in range(3)]
  pack(sy['_time_scalar_fields'],'H',n);pack(sy['_motion_position_state'],'3hH3i',*prev,0,*ic);pack(sy['_projection_state'],'9i',*q,*pq,*fine)
  pack(a4-0x66e2,'3h',*v);pack(a4-0x6704,'3i',*pos)
  reg(17,0x2000)
  for k in range(1,17):reg(k,k*0x10101)
  reg(5,a4);reg(8,sp);pack(sp,'I',ret)
  saved=[reg(k) for k in range(1,17)]
  ok(u.uc_emu_start(h,b,ret,1000000,10000));assert reg(18)==ret
  eligible=n==1 and all(abs(x)<=16383 for x in v+prev)
  if eligible:
   expect=[];carries=[]
   for j in range(3):
    total=(9*v[j]-7*prev[j])*4096+(9*q[j]-7*pq[j])//16+ic[j]*512+fine[j]
    assert -(1<<31)<=total<(1<<31)
    d=trunc(total);expect.append(pos[j]+d);carries.append(total-d*65536)
   assert struct.unpack('>3i',read(a4-0x6704,12))==tuple(expect),case
   assert struct.unpack('>3i',read(sy['_projection_state']+24,12))==tuple(carries),case
   assert read(sy['_motion_position_state']+8,12)==bytes(12)
   assert [reg(k) for k in range(1,17) if k!=8]==[saved[k-1] for k in range(1,17) if k!=8]
   fast+=1
  else:
   assert reg(9)==0x12345678,case
   assert struct.unpack('>3i',read(a4-0x6704,12))==tuple(pos)
   fall+=1
  assert reg(8)==sp+4
 result=dict(passed=True,actual_68000_helper_cases=fast,fallback_cases=fall,projection_update='stubbed; projected Q supplied directly',registers_and_stack_preserved=True)
 Path('tmp/position-combined-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:ok(u.uc_close(h))
