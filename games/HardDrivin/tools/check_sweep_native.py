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
import subprocess
source=Path('src/HardDrivinSweep.s').read_text();source=source[source.index('_sweep_loop_ptr:'):]
source=source.replace('_sweep_loop_ptr: dc.l 0','_sweep_loop_ptr: dc.l $10bb4c').replace('_sweep_finish_ptr: dc.l 0','_sweep_finish_ptr: dc.l $10bd14').replace('_sweep_hit_ptr: dc.l 0','_sweep_hit_ptr: dc.l $10bc0c')
asm=' org $400100\nDS_ACTIVE equ 24\n_dispatch_state equ $407000\n_time_scalar_fields equ $407100\n jmp _sweep_begin\n jmp _sweep_miss\n jmp _sweep_finish\n jmp _sweep_scale_delta\n jmp _sweep_box\n dc.l _sweep_state\n'+source
p=Path('tmp/sweep-native');p.with_suffix('.s').write_text(asm)
subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
module=p.with_suffix('.bin').read_bytes();state=struct.unpack_from('>I',module,30)[0]
codebase=0x100000;database=0x200000;a4=database+0x7ffe;bases=[codebase,database,0x300000]
def g(off):return database+off-0x8002
def call(pc):
 reg(17,0x2000);reg(5,a4);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
 err=u.uc_emu_start(h,pc,0x490000,1000000,20000)
 if err: print('FAIL',enabled,fields,depths,hex(pc),'regs',[(k,hex(reg(k))) for k in range(1,19)],flush=True)
 ok(err);assert reg(8)==0x4ffff4
results=[]
native_states={}
try:
 for enabled in [False,True]:
  for fields in [8,16]:
   for depths in [[],[100],[150,100],[100,150],[100,100],[25],[100,25],[25,100]]:
    ok(u.uc_close(h));h=P();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,0x44000007,I(1)));ok(u.uc_mem_map(h,0x100000,0x400000,7))
    for index,hu in enumerate(hunks()):
     b=bytearray(hu['data'])
     for off,dest in hu['relocs']:struct.pack_into('>I',b,off,struct.unpack_from('>I',b,off)[0]+bases[dest])
     write(bases[index],bytes(b))
    write(0x400100,module)
    write(a4-0x7fce,bytes.fromhex('4e75'));write(a4-0x7fe0,bytes.fromhex('4e75'))
    if enabled:
     write(codebase+0xbd0e,bytes.fromhex('4ef9')+struct.pack('>I',0x400106))
     write(codebase+0xbd14,bytes.fromhex('4eb9')+struct.pack('>I',0x40010c))
    pack(g(0xb190),'h',len(depths));write(g(0xe931),b'\x00');write(g(0xe960),b'\x00');pack(g(0xe93a),'4h',0,16384,0,16384)
    for i,depth in enumerate(depths):
     obj=0x350000+i*64;pack(g(0xaf38)+6*i,'HI',0,obj);write(obj,bytes(40));pack(obj,'3h',0,0,depth);write(obj+25,b'\x01');write(obj+28,b'\x08');write(obj+34,bytes([255 if depth==25 else 0]))
    pack(g(0xaf04),'h',0);write(g(0x9606),b'\x00');pack(g(0x9928),'h',400);pack(g(0x992c),'h',112);pack(g(0x991e),'3h',0,0,600)
    pack(g(0x98fc),'3i',0,0,0);write(0x407018,b'\xff');pack(0x407100,'H',fields);call(0x400100)
    pack(g(0x9904),'i',1200);call(codebase+0xbaee)
    crash=read(g(0x9606),1)[0];z=struct.unpack('>i',read(g(0x9904),4))[0];best=struct.unpack('>I',read(state+42,4))[0];hits=struct.unpack('>I',read(state+58,4))[0];overflow=struct.unpack('>I',read(state+62,4))[0]
    native_hit=25 in depths
    swept=enabled and fields>8 and bool(depths) and not native_hit
    expected=native_hit or swept
    assert (crash==25)==expected,(enabled,fields,depths,crash,z)
    if swept:
     assert z==-1016,(z,depths)
     assert best==0x350000+depths.index(min(depths))*64,(best,depths)
     assert hits==1 and overflow==0
    if not swept:
     snapshot=read(g(0x98f6),0x9952-0x98f6)+read(g(0x9606),1)
     key=(fields,tuple(depths))
     if not enabled:native_states[key]=snapshot
     else:assert snapshot==native_states[key],('native state changed',key)
     assert hits==0 and overflow==0
    results.append(dict(enabled=enabled,fields=fields,depths=depths,crash=crash,z=z,hits=hits,overflow=overflow))
 # Test actual signed interpolation helper, including full 32-bit extrema.
 rng=random.Random(63000)
 for _ in range(10000):
  delta=rng.choice([-2147483648,2147483647,rng.randrange(-2147483648,2147483648)])
  denominator=rng.randrange(1,65536);numerator=rng.randrange(denominator+1)
  reg(9,delta&0xffffffff);reg(10,numerator);reg(11,denominator);call(0x400112)
  expected=abs(delta)*numerator//denominator*(-1 if delta<0 else 1)
  assert reg(9)==expected&0xffffffff,(delta,numerator,denominator,reg(9),expected)
 report=dict(passed=True,native_loop_cases=len(results),interpolation_cases=10000,results=results,scope='Actual native object loop with new gates, private scene coordinates and audio stubs. Crossing caught once, earliest object independent of enumeration, native interval unchanged. Live scene/culling/contact acceptance remains open.')
 Path('tmp/sweep-native-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
finally:ok(u.uc_close(h))
