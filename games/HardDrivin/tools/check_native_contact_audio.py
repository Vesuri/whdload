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
source=Path('src/HardDrivinAudio.s').read_text()
helpers=source[source.index('_audio_object_contact_due:'):source.index('\tIFD VERIFY_AUDIO_MATH\n_audio_math_test:')]
constants='AU_WALL equ 0\nAU_STEP equ 4\nAU_REQUESTS equ 8\nAU_EMITTED equ 12\nAU_VALID equ 16\nAU_SIZE equ 20\nAU_OBJECT equ AU_SIZE\n'
codebase=0x100000;database=0x200000;a4=database+0x7ffe
bases=[codebase,database,0x300000]
def g(off):return database+off-0x8002
def assemble(stem,text):
 p=Path('tmp')/stem;p.with_suffix('.s').write_text(text)
 subprocess.run([os.environ['VASM'],'-m68000','-Fbin','-devpac','-o',str(p.with_suffix('.bin')),str(p.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
 return p.with_suffix('.bin').read_bytes()
stub=assemble('collision-native-sound-stub',' org $400000\n move.w 4(sp),$480000\n addq.l #1,$480004\n rts\n')
results=[]
try:
 for kind,site,event in [('obstacle',0xbdde,7),('special',0xbc14,9)]:
  start=source.index('_audio_'+kind+'_contact:\n');end=source.index('\n_audio_',start+1) if kind!='special' else source.index('; A3 identifies the collided object.',start)
  wrapper=source[start:end]
  asm=' org $400100\nDS_ACTIVE equ 24\nDS_STEPS equ 8\nRP_WALL equ 0\n_dispatch_state equ $406040\n_replay_state equ $406080\n_audio_'+kind+'_state equ $406000\n'+constants+wrapper+'\n'+helpers
  gate=assemble('collision-native-'+kind,asm)
  for interval in [1,2,8,16]:
   for projection,mph in [((0,0,0),0),((20,-3,7),45),((20,-3,7),46)]:
    states=[]
    for enabled in [False,True]:
     ok(u.uc_close(h));h=P();ok(u.uc_open(7,1<<30,C.byref(h)));ok(u.uc_ctl(h,0x44000007,I(1)));ok(u.uc_mem_map(h,0x100000,0x400000,7))
     for index,hu in enumerate(hunks()):
      b=bytearray(hu['data'])
      for off,dest in hu['relocs']:struct.pack_into('>I',b,off,struct.unpack_from('>I',b,off)[0]+bases[dest])
      write(bases[index],bytes(b))
     write(0x400000,stub);write(0x400100,gate)
     write(a4-0x7fce,bytes.fromhex('4ef9')+struct.pack('>I',0x400000))
     write(a4-0x7fe0,bytes.fromhex('4e75')) # Private audio-stop stub for crash branch.
     if enabled:write(codebase+site,bytes.fromhex('4eb9')+struct.pack('>I',0x400100)+bytes.fromhex('4e714e71'))
     obj=0x350000
     pack(g(0xb190),'h',1);pack(g(0xaf38),'HI',0,obj)
     write(g(0xe931),bytes([kind=='obstacle']));write(g(0xe960),b'\xff')
     pack(g(0xe93a),'4h',0,16384,0,16384)
     write(obj,bytes(40));pack(obj,'3h',0,0,10);write(obj+25,bytes([95 if kind=='special' else 1]));write(obj+34,b'\xff')
     write(0x406058,b'\xff')
     visits=[]
     for step in range(1,18):
      # No render rearm on visits 5/6: obstacle flag was consumed by visit4.
      rearm=step not in (5,6)
      if rearm:write(obj+32,b'\xff')
      write(g(0x9606),b'\x00');pack(g(0x9928),'h',0 if not any(projection) else 100);pack(g(0x992c),'h',mph)
      pack(g(0x991e),'3h',*projection);pack(g(0x98fc),'3i',10000,20000,30000)
      pack(0x406048,'I',step);pack(0x406080,'I',100+(step-1)*interval)
      previous=struct.unpack('>I',read(0x480004,4))[0]
      reg(17,0x2000);reg(5,a4);reg(8,0x4ffff0);pack(0x4ffff0,'I',0x490000)
      ok(u.uc_emu_start(h,codebase+0xbaee,0x490000,1000000,10000))
      assert reg(8)==0x4ffff4
      emitted=struct.unpack('>I',read(0x480004,4))[0]-previous
      expected_arg=9 if kind=='special' else (7 if mph<=45 else 6)
      if emitted:assert struct.unpack('>H',read(0x480000,2))[0]==expected_arg
      if kind=='special':assert read(g(0x98fc),12)==struct.pack('>3i',10000,20000,30000)
      elif rearm:
       assert read(g(0x9908),6)==struct.pack('>3h',*[-v for v in projection])
       assert read(g(0x98fc),12)==struct.pack('>3i',*[v-2*p for v,p in zip([10000,20000,30000],projection)])
       assert read(obj+32,1)==b'\x00'
      visits.append(dict(step=step,rearm=rearm,emitted=emitted,game_state=read(g(0x98f6),0x9952-0x98f6).hex(),crash=read(g(0x9606),1).hex()))
     states.append(visits)
    assert all(x['game_state']==y['game_state'] and x['crash']==y['crash'] for x,y in zip(*states))
    last=None;laststep=None
    for original,patched in zip(*states):
     eligible=kind=='special' or original['rearm'];step=original['step'];now=100+(step-1)*interval
     assert original['emitted']==int(eligible)
     impulse=kind=='obstacle' and any(projection)
     due=eligible and (impulse or last is None or step-laststep>1 or now-last>=8)
     if eligible:
      if due:last=now if impulse or last is None or step-laststep>1 else now-((now-last)&7)
      laststep=step
     assert patched['emitted']==int(due),(kind,interval,projection,step,patched['emitted'],due)
    results.append(dict(kind=kind,interval=interval,projection=projection,mph=mph,original=sum(v['emitted'] for v in states[0]),patched=sum(v['emitted'] for v in states[1]),visits=17))
 result=dict(passed=True,configurations=len(results),native_collision_calls=len(results)*34,results=results,scope='Pristine relocated collision routine with private object/global fixtures, actual new hook at its native site, private sound/stop handlers. Physics/impulses unchanged; no natural-route, renderer-flag-generation, sample-start or audible-quality claim.')
 Path('tmp/collision-native-audio.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:ok(u.uc_close(h))
