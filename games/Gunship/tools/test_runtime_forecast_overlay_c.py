from unicorn_b import *
from functools import lru_cache
import json
base=0x100000;l=(root/'tmp/c/runtime.lst').read_text();live=(build/'selector-combat.slave.lst').read_text(encoding='latin1')
@lru_cache(None)
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',l,re.M)[1],16)
@lru_cache(None)
def ls(n):return int(re.search(r'^([0-9A-F]{8}) '+n+'$',live,re.M)[1],16)
folder=root/'tmp/c/homing-selection-pal-060';reports=[]
MEM=C.CFUNCTYPE(None,C.c_void_p,C.c_int,C.c_uint64,C.c_int,C.c_int64,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
for world in (27,45):
 d=folder/f'world-{world}';a=(d/'arena.bin').read_bytes();h=struct.unpack_from('>9I',a,ls('RT_HUNKS'));c=CPU()
 c.put(0x200000,(folder/'fast.bin').read_bytes());c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data()))
 for i in (0,2,4,5,6):c.put(h[i],(d/f'h{i}.bin').read_bytes())
 for off,op in ((0x5d20,0x1239),(0x68a2,0x1439),(0x68d2,0x1439)):c.put(h[0]+off,struct.pack('>HI',op,h[6]+0x3ce3))
 for off in (0x6356,0x63d4):c.put(h[0]+off,struct.pack('>HI',0x4eb9,h[0]+0xa450))
 arena=0x400000;rf=arena+sym('RT_FORECAST');ap=arena+sym('RT_ACTOR_PREVIEW');c.put(arena,a)
 # World snapshots were taken inside a batch. Explicitly model a drained
 # boundary at this same world phase; no claim about the pending input batch.
 for off in ('RT_BATCH',):c.put(arena+sym(off),bytes(2))
 for off in ('TS_STATE','TS_FIELDS','TS_TICKS','TS_EXCESS'):c.put(arena+sym('RT_SCHEDULER')+sym(off),bytes(2))
 def call(name,args):
  regs={r:0x1700+r for r in range(1,17) if r!=8};regs.update(args)
  for r,v in regs.items():c.rw(r,v)
  c.rw(8,0x8f000);c.call(base+sym(name));assert c.rr(18)==0x90000,(name,c.rr(18))
  assert all(c.rr(r)==v for r,v in regs.items() if r!=9),name
  return c.rr(9)
 assert call('timing_runtime_forecast_prepare',{1:arena})==0
 assert call('motion_stages_prepare',{1:h[0],2:arena+sym('RT_STAGES')})==0
 assert call('actor_preview_prepare',{1:h[0],2:h[6],3:ap})==0
 assert call('actor_present_capture',{1:arena+sym('RT_ACTOR_PRESENT'),2:ap,3:arena+sym('RT_ACTOR_GENERATIONS'),4:h[6]+0x3b88,9:world,10:int.from_bytes(c.get(arena+sym('RT_CLOCK')+sym('TC_PHASE'),2),'big')})==0
 checking=[True]
 native={i:c.get(h[i],len((d/f'h{i}.bin').read_bytes())) for i in (0,2,4,5,6)}
 authoritative=c.get(arena,sym('RT_FORECAST'));bad=[]
 @MEM
 def write(handle,kind,addr,n,value,user):
  if checking[0] and not(rf<=addr and addr+n<=arena+sym('RT_ARENA_SIZE') or arena+sym('RT_ACTOR_COORDS')<=addr and addr+n<=arena+sym('RT_ACTOR_COORDS')+36 or ap<=addr and addr+n<=ap+sym('AP_SIZE') or 0x8e000<=addr and addr+n<=0x8f004):bad.append((hex(addr),n))
 hk=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hk),1<<11,write,None,1,0))
 status=call('timing_runtime_forecast_actors',{1:arena})
 if world<27:
  assert status==0xfffffffd and c.get(rf+sym('RF_ACTOR_SAFE'),2)==bytes(2),(world,status)
 else:
  assert status&32 and status<64,(world,status)
  pose=[c.get(rf+sym('RF_ACTOR_NEXT')+12*axis+10,2).hex() for axis in range(3)]
  n=(folder/f'world-{world+1}'/'h0.bin').read_bytes();want=[n[0xc6a0+12*axis+10:0xc6a0+12*axis+12].hex() for axis in range(3)]
  assert pose==want,(world,pose,want)
  assert int.from_bytes(c.get(rf+sym('RF_ACTOR_SAFE'),2),'big')==status
 anchor=int.from_bytes(c.get(arena+sym('RT_CLOCK')+sym('TC_PHASE'),2),'big');span=(50-anchor+2)//3
 initial=c.get(h[0]+0xc6a0,36);endpoint=c.get(rf+sym('RF_ACTOR_NEXT'),36)
 checking[0]=False
 c.put(arena+sym('RT_PACKET')+4,bytes(6))
 assert call('endpoint_player_begin',{1:arena+sym('RT_ENDPOINT'),2:h[6]+0x3b88,9:span,10:world+1})==0
 checking[0]=True
 for elapsed in range(span):
  if elapsed:
   checking[0]=False
   owner=arena+sym('RT_ENDPOINT');field=int.from_bytes(c.get(owner+sym('EP_DELAY')+sym('CD_FIELD'),4),'big')+1
   assert call('endpoint_player_step',{1:owner,2:h[6]+0x3b88,3:arena+sym('RT_STAGES'),4:h[0]+0x7a44,5:arena+sym('RT_PACKET'),9:field})==0
   c.put(arena+sym('RT_CLOCK')+sym('TC_PHASE'),struct.pack('>H',anchor+3*elapsed));checking[0]=True
  if elapsed not in (0,span//2,span-1):continue
  native={i:c.get(h[i],len((d/f'h{i}.bin').read_bytes())) for i in (0,2,4,5,6)}
  authoritative=c.get(arena,sym('RT_FORECAST'))
  mask=call('timing_runtime_forecast_present',{1:arena});assert mask&32 and mask<64,(world,elapsed,mask)
  for axis in range(3):
   off=axis*12+10;start=int.from_bytes(initial[off:off+2],'big');end=int.from_bytes(endpoint[off:off+2],'big');delta=((end-start+32768)&65535)-32768
   want=(start+delta*elapsed//span)&65535
   assert int.from_bytes(c.get(rf+sym('RF_PRESENT_COORDS')+off,2),'big')==want,(world,elapsed,axis)
  visual=c.get(rf+sym('RF_PRESENT_COORDS'),36)
  output=arena+sym('RT_ACTOR_COORDS');sentinel=b'Z'*36;c.put(output,sentinel)
  assert call('timing_runtime_forecast_overlay',{1:arena})==0
  got=c.get(output,36)
  for slot in range(6):
   for axis in range(3):
    off=axis*12+slot*2
    assert got[off:off+2]==(visual[off:off+2] if slot==5 else sentinel[off:off+2]),(world,elapsed,slot,axis)
  # Bit-3 guidance takes precedence over bit-7 homing and must avoid forecasting.
  flag=h[0]+0xc6d6+5;oldflag=c.get(flag,1);c.put(flag,b'\x88');attempts=c.get(rf+sym('RF_ATTEMPTS'),4)
  c.put(output,sentinel);assert call('timing_runtime_forecast_overlay',{1:arena})==0
  assert c.get(output,36)==sentinel and c.get(rf+sym('RF_ATTEMPTS'),4)==attempts;c.put(flag,oldflag)

  assert call('timing_runtime_forecast_present',{1:arena})==mask and c.get(rf+sym('RF_PRESENT_COORDS'),36)==visual
  assert all(c.get(h[i],len(v))==v for i,v in native.items())
 # Constructor identity change must suppress the forecast for this slot.
 generation=arena+sym('RT_ACTOR_GENERATIONS')+20
 c.put(generation,struct.pack('>I',(int.from_bytes(c.get(generation,4),'big')+1)&0xffffffff))
 authoritative=c.get(arena,sym('RT_FORECAST'))
 mask=call('timing_runtime_forecast_present',{1:arena});assert mask<64 and not mask&32
 for axis in range(3):assert c.get(rf+sym('RF_PRESENT_COORDS')+axis*12+10,2)==initial[axis*12+10:axis*12+12]
 after=bytearray(c.get(arena,sym('RT_FORECAST')));before=bytearray(authoritative)
 off=sym('RT_ACTOR_PREVIEW');after[off:off+sym('AP_SIZE')]=before[off:off+sym('AP_SIZE')]
 off=sym('RT_ACTOR_COORDS');after[off:off+36]=before[off:off+36]
 assert after==before and not bad,bad
 assert all(c.get(h[i],len(v))==v for i,v in native.items())
 # Failed admission must retire the previous slot mask.
 c.put(arena+sym('RT_BATCH'),struct.pack('>H',1));assert call('timing_runtime_forecast_actors',{1:arena})==0xfffffffd
 assert c.get(rf+sym('RF_ACTOR_SAFE'),2)==bytes(2)
 reports.append(dict(world=world,admitted=world>=27,status=status,pose=pose if world>=27 else None));c.close()
report=dict(status='passed',admitted=sum(r['admitted'] for r in reports),rejected=sum(not r['admitted'] for r in reports),known_retargets=[27,45],native_writes=0,fixture='world snapshots normalized to drained boundaries; held controls',reports=reports)
(root/'tmp/c/runtime-forecast-overlay-test.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k!='reports'})
