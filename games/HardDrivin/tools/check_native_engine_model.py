import ctypes as C,json,os,random,re,struct
from pathlib import Path
u=C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.dylib'))
P=C.c_void_p; U=C.c_uint64; Z=C.c_size_t; I=C.c_int
for name,args in [('uc_open',[I,I,C.POINTER(P)]),('uc_ctl',[P,C.c_uint32]),('uc_mem_map',[P,U,Z,C.c_uint32]),('uc_mem_write',[P,U,P,Z]),('uc_mem_read',[P,U,P,Z]),('uc_reg_write',[P,I,P]),('uc_reg_read',[P,I,P]),('uc_emu_start',[P,U,U,U,Z]),('uc_close',[P])]:
 f=getattr(u,name);f.argtypes=args;f.restype=I
u.uc_strerror.argtypes=[I];u.uc_strerror.restype=C.c_char_p
def ok(x):assert x==0,u.uc_strerror(x)
h=P();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,0x44000007,I(1)));ok(u.uc_mem_map(h,0x100000,0x400000,7))
def write(a,b):ok(u.uc_mem_write(h,a,b,len(b)))
def read(a,n):b=C.create_string_buffer(n);ok(u.uc_mem_read(h,a,b,n));return b.raw
def reg(k,v=None):
 x=C.c_uint32(v or 0)
 if v is None:ok(u.uc_reg_read(h,k,C.byref(x)));return x.value
 ok(u.uc_reg_write(h,k,C.byref(x)))
def pack(a,fmt,*v):write(a,struct.pack('>'+fmt,*v))
def trunc(x):return abs(x)//65536*(-1 if x<0 else 1)

import subprocess,sys
sys.path.insert(0,'tools')
from game_image import hunks
import random
import drivetrain_model as model
from audit_forward_force import word
codebase=0x100000;database=0x200000;a4=database+0x7ffe;bases=[codebase,database,0x300000]
def g(off):return database+off-0x8002
for index,hu in enumerate(hunks()):
 b=bytearray(hu['data'])
 for off,dest in hu['relocs']:struct.pack_into('>I',b,off,struct.unpack_from('>I',b,off)[0]+bases[dest])
 write(bases[index],bytes(b))
# The real math/vector table and engine execute unchanged; audio is ineligible.
write(g(0xaddc),b'\x00');write(g(0x9606),b'\x00');write(g(0x9910),b'\x0f');write(g(0xe94a),b'\xff');write(g(0xf791),b'\xff')
write(g(0xf790),b'\x00');write(g(0xaf31),b'\x00');write(g(0x993e),b'\xff')
rng=random.Random(2950)
cases=[(v,r,t,k) for k in range(1,5) for t in [0,22,63,64,75,100] for v in [0,40,100,225,500,1000] for r in [0,1950,5100,6500]]
cases += [(rng.randrange(1001),rng.randrange(6501),rng.randrange(101),rng.randrange(1,5)) for _ in range(1024)]
results=[]
try:
 for velocity,rpm,throttle,gear in cases:
  s=dict(velocity=velocity,velocity_carry=0,rpm=rpm,rpm_carry=0,rpm_last=rpm,rpm_gear=gear,gear=gear,throttle=throttle)
  pack(g(0x9928),'h',velocity);pack(g(0x992a),'h',rpm);pack(g(0x9936),'h',gear)
  pack(g(0x9926),'h',model.engine_speed(rpm,gear));write(g(0x991c),bytes([throttle]));write(g(0x9911),b'\x00')
  pack(g(0x9940),'I',0x350000+8*gear)
  reg(17,0x2000);reg(5,a4);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
  ok(u.uc_emu_start(h,codebase+0xb662,0x490000,1000000,10000));assert reg(8)==0x4ffff4
  actual={k:struct.unpack('>h',read(g(off),2))[0] for k,off in [('velocity',0x9928),('rpm',0x992a),('gear',0x9936)]}
  expected,_=model.advance(s,8);expected={k:expected[k] for k in actual}
  results.append(dict(input=s,actual=actual,expected=expected,match=actual==expected))
 bad=[r for r in results if not r['match']]
 report=dict(passed=not bad,cases=len(results),mismatches=len(bad),first_mismatches=bad[:10],results=results,scope='Actual pristine relocated engine, flat road/full contact/no brake/no skid/automatic, native n8. Original helpers and data table. No sound call, renderer or full-car proof.')
 Path('tmp/native-engine-model.json').write_text(json.dumps(report,indent=2)+'\n');print('cases',len(results),'mismatches',len(bad),'examples',json.dumps(bad[:3]))
finally:ok(u.uc_close(h))
