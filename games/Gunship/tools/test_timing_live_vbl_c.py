"""VBL ownership ABI and atomic installer checks against actual slave."""
import random,json
from unicorn_b import *
from amitools.binfmt.Relocate import Relocate
blob=bytes(BinFmt().load_image(str(build/'release/Gunship.Slave')).get_segments()[0].get_data())
listing=(build/'release/Gunship.lst').read_text(encoding='latin1')
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob)
ARENA=0x300000;H0=0x400000;H6=0x4c0000;REF=0x700000
owner=ARENA+addr('RT_CAPTURE_OWNER')-base
c.put(addr('timing_runtime_arena'),struct.pack('>I',ARENA))
c.put(ARENA+addr('RT_HUNKS')-base+24,struct.pack('>I',H6))
rng=random.Random(42)
def state(flags):
 rs={r:rng.randrange(0x1000000) for r in range(1,17)}
 rs.update({8:0x8f000,17:0x2000|flags});return rs
def run(entry,rs):
 c.rw(17,rs[17])
 for r,v in rs.items():
  if r!=17:c.rw(r,v)
 c.put(0x90000,bytes.fromhex('40f900730000'));c.call(entry,end=0x90006)
 out={r:c.rr(r) for r in range(1,18)};out[17]=int.from_bytes(c.get(0x730000,2),'big');return out
cases=0
for name,off in [('weapon',0x4296),('ground',0x42f6),('hit',0x42f7)]:
 REF=0x700000+off*2
 c.put(REF,bytes.fromhex('5339')+struct.pack('>I',H6+off)+bytes.fromhex('4e75'))
 for flags in range(32):
  for value in (range(256) if flags==0 else (0,1,2,0x7e,0x7f,0x80,0x81,0xfe,0xff)):
   rs=state(flags);c.put(H6+off,bytes([value]));want=run(REF,rs)
   for enabled in (0,1):
    c.put(owner,struct.pack('>H',enabled));c.put(H6+off,bytes([value]))
    got=run(addr('timing_vbl_timer_'+name),rs)
    assert got==want,(name,flags,value,enabled,got,want)
    assert c.get(H6+off,1)==bytes([value if enabled else (value-1)&255]);cases+=1
# An RTS native target proves that even incoming flags survive the trampoline.
c.put(0x710000,bytes.fromhex('4e75'));c.put(addr('timing_vbl_native_guidance'),struct.pack('>I',0x710000))
for flags in range(32):
 rs=state(flags);want=run(0x710000,rs)
 for enabled in (0,1):
  c.put(owner,struct.pack('>H',enabled));assert run(addr('timing_vbl_guidance'),rs)==want;cases+=1
# Native keyboard ownership during a retained UI boundary must not unfreeze VBL state.
phase=ARENA+addr('RT_BOUNDARY_PHASE')-base
c.put(owner,bytes(2));c.put(0x712000,bytes.fromhex('52b9007350004e75'));c.put(0x713000,bytes.fromhex('4e75'))
c.put(addr('timing_vbl_native_guidance'),struct.pack('>I',0x712000));c.put(0x735000,bytes(4))
rs=state(31);run(addr('timing_vbl_guidance'),rs);assert c.get(0x735000,4)==b'\0\0\0\1'
for suspended in range(1,7):
 c.put(phase,struct.pack('>H',suspended))
 for name,off in [('weapon',0x4296),('ground',0x42f6),('hit',0x42f7)]:
  rs=state(31);c.put(H6+off,b'\x80');want=run(0x700000+off*2,rs);c.put(H6+off,b'\x80')
  assert run(addr('timing_vbl_timer_'+name),rs)==want and c.get(H6+off,1)==b'\x80'
 rs=state(31);want=run(0x713000,rs);assert run(addr('timing_vbl_guidance'),rs)==want
 assert c.get(0x735000,4)==b'\0\0\0\1'
c.put(phase,bytes(2))
# Real relocated image: validate all four addresses, defaults, and corruptions.
img=BinFmt().load_image(str(root/'tmp/game/Gunship/data/gamemule'))
addresses=[H0+i*0x20000 for i in range(len(img.get_segments()))]
original=bytes(Relocate(img).relocate(addresses)[0]);c.put(H0,original)
c.put(ARENA+addr('RT_HUNKS')-base,struct.pack('>9I',*addresses));c.put(ARENA,struct.pack('>I',1))
resload=0x740000;c.put(resload+0x64,bytes.fromhex('23c90075000023c8007500044e75'))
sites=[(0x4ba8,'timer_weapon'),(0x4bba,'timer_ground'),(0x4c32,'timer_hit'),(0x4c12,'guidance')]
for enabled in (0,1):
 c.put(addr('_custom1'),struct.pack('>I',enabled));c.put(0x750000,bytes(8))
 rs=state(0);rs.update({1:ARENA,3:resload});got=run(addr('timing_vbl_install'),rs);assert got[9]==0
 if enabled:
  image,patches=struct.unpack('>II',c.get(0x750000,8));assert image==H0
  for n,(off,target) in enumerate(sites):
   cmd,site,relative=struct.unpack('>HHh',c.get(patches+n*6,6));assert cmd==0x8003 and site==off and patches+relative==addr('timing_vbl_'+target)
  cmd,site,relative,skip=struct.unpack('>HHhH',c.get(patches+24,8));assert cmd==0x8010 and site==0x4c40 and patches+relative==addr('timing_vbl_effect_timers') and skip==30
  assert c.get(patches+32,2)==bytes(2)
 else:assert c.get(0x750000,8)==bytes(8)
 assert c.get(H0,len(original))==original
rejects=0
for site,_ in sites+[(0x4c40+6*k,'effect_timers') for k in range(6)]:
 for delta in (0,2,4):
  off=site+delta;saved=c.get(H0+off,2);c.put(H0+off,bytes(v^1 for v in saved));c.put(0x750000,bytes(8))
  rs=state(0);rs.update({1:ARENA,3:resload});got=run(addr('timing_vbl_install'),rs)
  assert got[9]==0xffffffff and c.get(0x750000,8)==bytes(8);c.put(H0+off,saved);rejects+=1
c.put(ARENA,bytes(4));c.put(0x750000,bytes(8));assert run(addr('timing_vbl_install'),rs)[9]==0xffffffff and c.get(0x750000,8)==bytes(8)
print(json.dumps(dict(status='passed',abi_cases=cases,signature_rejections=rejects,custom_gate=True,ready_gate=True)));c.close()
