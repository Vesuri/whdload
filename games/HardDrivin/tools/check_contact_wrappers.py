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

source=Path('src/HardDrivinAudio.s').read_text()
import subprocess
helpers=source[source.index('_audio_object_contact_due:'):source.index('\tIFD VERIFY_AUDIO_MATH\n_audio_math_test:')]
constants='AU_WALL equ 0\nAU_STEP equ 4\nAU_REQUESTS equ 8\nAU_EMITTED equ 12\nAU_VALID equ 16\nAU_SIZE equ 20\nAU_OBJECT equ AU_SIZE\n'
results=[];rng=random.Random(812901)
try:
 for kind,event in [('object',7),('obstacle',7),('special',9)]:
  start=source.index('_audio_'+kind+'_contact:\n')
  end=source.index('\n_audio_',start+1) if kind!='special' else source.index('; A3 identifies the collided object.',start)
  wrapper=source[start:end]
  for native in [False,True]:
   # New CPU instance avoids stale translated code when variants share addresses.
   ok(u.uc_close(h));h=P();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,0x44000007,I(1)));ok(u.uc_mem_map(h,0x10000,0x40000,7))
   stem=Path('tmp')/('contact-wrapper-'+kind+('-native' if native else ''))
   asm=' org $10000\nDS_ACTIVE equ 24\nDS_STEPS equ 8\nRP_WALL equ 0\n_dispatch_state equ $17040\n_replay_state equ $17080\n_audio_'+kind+'_state equ $17000\n'
   if native:asm+='VERIFY_DISPATCH_NATIVE equ 1\n'
   asm+=' bsr _audio_'+kind+'_contact\n move.w sr,$31008\n jmp $20000\n'+constants+wrapper+'\n'+helpers
   stem.with_suffix('.s').write_text(asm)
   subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
   write(0x10000,stem.with_suffix('.bin').read_bytes())
   write(0x20032,Path('tmp/object-stub-micro.bin').read_bytes())
   checks=0
   for case in range(512):
    active=case%2; xflag=(case//2%2)*16;valid=255 if case%7 else 0
    projection=rng.choice([(0,0,0),(1,0,0),(0,1,0),(0,0,-1)])
    obj=0x34560;oldobj=rng.choice([obj,0x34590]);last=rng.choice([100,0xfffffff8,0xfffffffc])
    now=(last+rng.choice([0,1,7,8,9,16,65535]))&0xffffffff
    oldstep=rng.choice([9,0xffffffff]);gap=rng.choice([0,1,2,4]);step=(oldstep+gap)&0xffffffff
    initial=struct.pack('>4IB3xI',last,oldstep,13,9,valid,oldobj)
    write(0x17000,initial);write(0x17040,bytes(32));pack(0x17048,'I',step);write(0x17058,bytes([active]));pack(0x17080,'I',now)
    write(0x31000,bytes(12));pack(0x2191e,'3h',*projection)
    reg(17,0x2000|xflag)
    for k in range(1,17):reg(k,k*0x10101)
    reg(4,obj);reg(5,0x28000);reg(8,0x4fff0);saved=[reg(k) for k in range(1,17)]
    expected=initial;emit=True
    if active and not native:
     reset=not valid or oldobj!=obj or (kind!='special' and any(projection))
     elapsed=(now-last)&0xffffffff
     emit=reset or gap>1 or (gap==1 and elapsed>=8)
     wall=last
     if emit:wall=now if reset or gap>1 else (now-(elapsed&7))&0xffffffff
     expected=struct.pack('>4IB3xI',wall,step,14,9+int(emit),255 if emit else valid,obj)
    ok(u.uc_emu_start(h,0x10000,0x20000,1000000,1000))
    assert reg(8)==0x4fff0
    assert all(reg(k)==saved[k-1] for k in range(1,17) if k!=9)
    assert reg(9)==(85 if emit else saved[8])
    arg,unused,calls,ccr=struct.unpack('>HHIH',read(0x31000,10))
    assert calls==int(emit) and arg==(event if emit else 0),(kind,native,case)
    assert ccr&16==(0 if emit else xflag)
    assert read(0x17000,24)==expected,(kind,native,case,read(0x17000,24).hex(),expected.hex())
    checks+=1
   results.append(dict(kind=kind,native=native,cases=checks))
 result=dict(passed=True,actual_68000_wrapper_cases=sum(r['cases'] for r in results),checks=results,scope='Assembled actual wrappers with private sound handler; identity, impulse, cadence, wall/serial wrap, inactive/native behavior, register/stack/X preservation. Not live contact or audible output.')
 Path('tmp/contact-wrappers-micro.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
finally:ok(u.uc_close(h))
