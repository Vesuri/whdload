#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/scheduled-world.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/scheduled-world.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
whole=0x300000;stages=0x310000;p=h[6]+0x3b88;out=0x320100;terms=0x320200;state=0x320300;rng=random.Random(9636);calls=0
trunc=lambda n,d:-(abs(n)//d) if n<0 else n//d
signed=lambda n:n-2**32 if n&2**31 else n
sb=lambda n:(n&255)-256 if n&128 else n&255
sw=lambda n:(n&65535)-65536 if n&32768 else n&65535
def call(name,ptrs):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};regs.update(ptrs)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(base+sym(name));calls+=1
 assert c.rr(18)==0x90000 and c.rr(8)==0x8f004
 for r,v in regs.items():
  if r==9 or r==10 and name=='fraction_add_rate':continue
  assert c.rr(r)==v,(name,r)
 return c.rr(9)
def long(off):return struct.unpack('>i',c.get(state+off,4))[0]
def qvalue(off,rate,conversion=None):return F(long(off),32767)+(F(long(conversion),rate*32767) if conversion else 0)
assert call('motion_preview_prepare',{1:h[0],2:whole})==0
assert call('motion_stages_prepare',{1:h[0],2:stages})==0
fixtures=json.loads((root/'tmp/c/player-motion-fixtures.json').read_text())



TS=0x400000;TC=0x401000;TH=0x402000;CQ=0x404000;rec=0x405000;sample=0x406000;shadow=0x408000;packet=0x409000;camera=0x40a000
context=0x420000;candidate=0x421000;delay=0x422000
CP=0x430000;CW=0x431000;MODE=0x432000;DEC=0x433000
assert call('world_commands_prepare',{1:h[0],2:DEC})==0
for off in [0xaf36,0xa150,0xb4e4,0xb57c,0xb0a6,0xb2e0]:c.put(h[0]+off,bytes.fromhex('4e75'))
RC=0x500000;FIRE=0x501000;HIT=0x502000;WEAPONS=0x503000;DAMAGE=0x504000;EFFECTS=0x505000;HEADING=0x506000
SCRIPT=0x507000;RESERVES=0x508000;PERIODIC=0x509000;CLEANUP=0x50a000;BODY=0x50b000;OPENING=0x50c000
FG=0x50d000;SG=0x50e000;PENDING=0x50f000;GROUND=0x510000;EVENT=0x511000;SW=0x512000
c.put(h[0]+0xc654,bytes.fromhex('70054e75'));c.put(h[0]+0x7fa4,bytes.fromhex('70004e75'))
for name,args in [
 ('world_rng_prepare',{1:h[0]+0x7a5c,2:RC,3:rec,4:h[2]}),
 ('world_hit_prepare',{1:h[0],2:HIT,3:RC}),
 ('world_effect_prepare',{1:h[0],2:EFFECTS,3:RC,4:HEADING}),
 ('world_weapons_prepare',{1:h[0],2:WEAPONS,3:RC,4:FIRE,5:h[6]}),
 ('world_damage_prepare',{1:h[0],2:DAMAGE,3:RC,4:EFFECTS,5:HIT,6:h[6]}),
 ('world_script_prepare',{1:h[0],2:SCRIPT,3:RC,4:HIT,5:h[6]}),
 ('world_reserves_prepare',{1:h[0],2:RESERVES}),
 ('world_periodic_prepare',{1:h[0],2:PERIODIC,3:RC,4:h[6]}),
 ('world_cleanup_prepare',{1:h[0],2:CLEANUP,3:h[4]}),
 ('world_start_prepare',{1:h[0],2:OPENING,3:h[6],4:p}),
 ('field_guidance_prepare',{1:h[0],2:FG,3:h[4],4:PENDING}),
 ('ground_deferred_prepare',{1:h[0],2:GROUND,3:h[6],4:EVENT})]:assert call(name,args)==0
GEOMETRY=0x520000;GEOMETRY_CONTEXT=0x523000
assert call('scene_private_prepare',{1:h[0],2:h[6],3:GEOMETRY})==0
c.put(BODY,struct.pack('>7IH',p,WEAPONS,DAMAGE,SCRIPT,RESERVES,PERIODIC,CLEANUP,0))
low=0x97ee00;length=0x21200;initial=c.get(low,length)
CODE=C.CFUNCTYPE(None,C.c_void_p,C.c_uint64,C.c_uint32,C.c_void_p)
u.uc_hook_add.argtypes=[C.c_void_p,C.POINTER(C.c_size_t),C.c_int,C.c_void_p,C.c_void_p,C.c_uint64,C.c_uint64]
trace=[]
@CODE
def event(handle,a,n,user):trace.append(0x7f80 if a==RESERVES else a-h[0])
hooks=[]
for off in [0xbade,0xbf34,0xc3e0,0x7f80,0x8050]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,h[0]+off,h[0]+off));hooks.append(hook)
hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,RESERVES,RESERVES));hooks.append(hook)
for addr in [WEAPONS,DAMAGE,SCRIPT,CLEANUP]:
 hook=C.c_size_t();ok(u.uc_hook_add(c.h,C.byref(hook),1<<2,event,None,addr,addr));hooks.append(hook)
runs=[]
def word(a):return int.from_bytes(c.get(a,2),'big')
for rate in ([] if os.environ.get('GS_QUICK') else [50,60]):
 baseline=None
 for batch in [int(n) for n in os.environ.get('GS_BATCHES','1,3,10,25').split(',')]:
  c.put(low,initial)
  assert call('clock_init',{1:TC,9:0,10:rate})==0
  assert call('history_init',{1:TH,9:0})==0
  assert call('commands_init',{1:CQ,9:0})==0
  assert call('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})==0
  assert call('player_step_init',{1:shadow,9:rate,10:0})==0
  assert call('control_delay_init',{1:delay,9:rate,10:0})==0
  c.put(context,struct.pack('>6I',shadow,p,stages,h[0]+0x7a44,packet,candidate)+bytes(16)+struct.pack('>I',delay))
  b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,4096);struct.pack_into('>H',b,12,65532);struct.pack_into('>H',b,4,4096);b[27]=128;b[57]=26;b[66]=28;b[65]=1;b[17]=2;c.put(p,b)
  c.put(h[4]+0x1c5,bytes(2));c.put(h[4]+0x440,bytes(2));c.put(h[0]+0x9c42,bytes(1))
  c.put(h[0]+0xba08,bytes(4));c.put(h[0]+0xba0c,b'\xff\xff\xff\xff');c.put(h[6]+0x1558,bytes([99]*6));c.put(p+0x256+5,b'\x01')
  c.put(h[0]+0xa44d,b'\xff\0\0');c.put(h[0]+0xa436,bytes(1));c.put(PENDING,bytes(1))
  c.put(SG,struct.pack('>IIII',TS,h[6],h[4],FG)+bytes(8));c.put(SW,struct.pack('>III',TS,p,OPENING)+bytes(8));trace.clear()
  assert call('control_mode_init',{1:MODE,2:p})==0
  c.put(CP,struct.pack('>III',CQ,p,MODE)+bytes(12))
  c.put(CW,struct.pack('>IIII',CQ,p,DEC,h[0]+0xaf36)+bytes(12))
  c.put(GEOMETRY_CONTEXT,struct.pack('>IIII',TS,p,GEOMETRY,h[0]+0xc6a0)+bytes(10))
  tick=65532;completed=0;worlds=[];poses=[];lastheld=0;edges=0
  for first in range(1,361,batch):
   for f in range(first,min(first+batch,361)):
    x=[1,0,-1,0][(f//15)%4];y=[0,1,0,-1][(f//20)%4];held=(f//7)%4;edge=held&~lastheld;lastheld=held
    assert call('commands_publish',{1:CQ,9:f,10:[0x51,1,2,0x38,0x39,3,0x50,0x7f][f%8]})==1
    raw=struct.pack('>6IHhhHII',f,0xffff0000|(x&255),0x12340000|(y&255),held,0,f,8,77,-91,edge,123+f//50,f*17003%1000000)
    c.put(sample,raw);assert call('history_publish',{1:TH,2:sample})==1
   assert call('scheduler_begin',{1:TS,9:128,10:8})==0
   while True:
    got=call('scheduler_next',{1:TS,2:rec})
    if got==0:break
    assert got==1
    sample_field=int.from_bytes(c.get(rec,4),'big')
    assert c.get(rec+32,8)==struct.pack('>II',123+sample_field//50,sample_field*17003%1000000)
    assert call('scheduler_next',{1:TS,2:sample})==0xfffffffd
    assert call('controls_from_history',{1:rec,2:packet})==0
    edges|=word(rec+30)
    c.put(h[0]+0xc757,bytes([(sample_field+batch)&255]));c.put(h[2]+0x14,struct.pack('>II',batch,sample_field+batch))
    assert call('scheduled_field_vbl_state',{1:SG}) in [0,1]
    interval=(tick+1)&65535
    if word(TS+14):
     assert call('scheduled_world_start',{1:SW})==0
     tick=interval
    assert word(p+12)==tick
    before=c.get(p,86),c.get(shadow,76),c.get(delay,32)
    assert call('field_player_prepare_delayed',{1:context,2:TS,3:rec,9:interval})==0xfffffffd
    assert before==(c.get(p,86),c.get(shadow,76),c.get(delay,32)) and word(context+36)==0
    assert call('command_phase_player',{1:TS,2:CP,9:1})==0xfffffffe
    assert call('command_phase_player',{1:TS,2:CP,9:1})==0
    if word(TS+14):
     unchanged=c.get(p,86),c.get(shadow,76),c.get(delay,32)
     assert call('field_player_prepare_delayed',{1:context,2:TS,3:rec,9:interval})==0xfffffffd
     assert unchanged==(c.get(p,86),c.get(shadow,76),c.get(delay,32))
     while True:
      drained=call('command_phase_world_before_player',{1:TS,2:CW,9:3})
      if drained==0:break
      assert drained==0xfffffffe
     assert call('control_mode_check',{1:MODE,2:p})==0
    else:
     unchanged=c.get(p,86),c.get(CQ,1048)
     assert call('command_phase_world_before_player',{1:TS,2:CW,9:3})==0xfffffffd
     assert unchanged==(c.get(p,86),c.get(CQ,1048))
    if word(TS+14):assert call('world_motion_impulses',{1:p,2:packet,3:RC})==0
    before=c.get(p,86),c.get(shadow,76),c.get(delay,32)
    assert call('field_player_prepare_delayed',{1:context,2:TS,3:rec,9:interval})==0
    assert before==(c.get(p,86),c.get(shadow,76),c.get(delay,32)) and word(context+38)==0
    assert call('scheduler_next',{1:TS,2:sample})==0xfffffffd
    c.put(EVENT,bytes(4))
    if word(TS+14):assert call('ground_deferred_step',{1:candidate,2:candidate+76,3:GROUND,4:EVENT,9:word(candidate+72)}) in [0,1]
    due=call('field_player_complete',{1:context});assert due in [0,1]
    assert word(context+38)==1 and word(context+36)==0
    assert call('field_player_complete',{1:context})==0xfffffffd
    assert word(p+12)==tick
    assert int.from_bytes(c.get(delay+8,4),'big')==sample_field
    completed+=1;poses.append((c.get(p,86),c.get(shadow,76),c.get(delay,32)))
    assert word(TS+12)==(2 if due else 0)
    if due:
     assert call('scheduler_next',{1:TS,2:sample})==0xfffffffd
     assert word(TS+44)==edges
     while True:
      drained=call('command_phase_world',{1:TS,2:CW,9:3})
      if drained==0:break
      assert drained==0xfffffffe
     assert call('control_mode_check',{1:MODE,2:p})==0
     assert call('ground_deferred_commit',{1:EVENT,2:h[0]+0xa150,3:h[6]+0x42f6}) in [0,1]
     assert call('world_fire_prepare',{1:TS,2:FIRE})==0
     c.put(HEADING,bytes([c.get(p+53,1)[0],0]));c.put(BODY+28,bytes(2))
     result=call('world_scene_body_step',{1:BODY,2:GEOMETRY_CONTEXT});assert result==0,('world-boundary',rate,batch,sample_field,result)
     assert call('scheduled_world_scene',{1:GEOMETRY_CONTEXT})==0xfffffffd
     assert word(p+28)>0,('contact fixture',rate,batch,sample_field)
     worldstate=bytearray(c.get(low,length))
     for addr,size in [(h[2]+0x14,8),(h[0]+0xc757,1)]:worldstate[addr-low:addr-low+size]=bytes(size)
     worlds.append((sample_field,bytes(worldstate),list(trace)))
     assert call('scheduler_world_done',{1:TS})==0;edges=0
   before=c.get(p,86),c.get(shadow,76),c.get(delay,32)
   assert call('player_camera_angles',{1:p,2:shadow,3:camera})==0
   assert before==(c.get(p,86),c.get(shadow,76),c.get(delay,32))
  assert 0xbade in trace and 0xbf34 in trace and 0x7f80 in trace,(rate,batch,trace)
  assert 0x8050 not in trace
  result=(poses,worlds,c.get(p,86),c.get(shadow,76),c.get(delay,32),c.get(camera+6,6))
  if baseline is None:baseline=result
  else:assert result==baseline,(rate,batch)
  assert completed==360 and len(worlds)==360*3//rate
  assert int.from_bytes(c.get(TS+32,4),'big')==360 and int.from_bytes(c.get(TS+36,4),'big')==len(worlds)
  runs.append(dict(rate=rate,batch=batch,fields=completed,world_observations=len(worlds),clock=tick,launches=trace.count(0xbade),actor_visits=trace.count(0xbf34),periodic_checks=trace.count(0x7f80)))

# Positive geometry must jump directly to native cleanup, once.
c.put(low,initial)
for name,args in [('clock_init',{1:TC,9:0,10:50}),('history_init',{1:TH,9:0}),('commands_init',{1:CQ,9:0}),('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})]:assert call(name,args)==0
c.put(TS+12,struct.pack('>HH',2,1));c.put(TS+24,struct.pack('>I',123))
c.put(GEOMETRY_CONTEXT,struct.pack('>IIII',TS,p,GEOMETRY,h[0]+0xc6a0)+bytes(10));c.put(BODY+28,bytes(2))
c.put(p,struct.pack('>HH',0x7fff,0x7fff));c.put(p+0x1c,bytes(2));c.put(p+0x35,bytes(3));c.put(p+0x1a,b'\0');c.put(p+0x18,b'\0');c.put(h[0]+0xba08,bytes(2))
for off,v in zip([0x3be3,0x3c5d,0x3c63,0x3cdd,0x3ddd,0x3d5d],struct.pack('>HHH',0x7fff,0x7fff,24)):c.put(h[6]+off,bytes([v]))
before=c.get(low,length)
c.put(p+0x18,b'\1');c.rw(6,p);c.rw(8,0x8f000);c.call(CLEANUP);assert c.rr(18)==0x90000
expected=c.get(low,length)
c.put(low,before);trace.clear()
assert call('world_scene_body_step',{1:BODY,2:GEOMETRY_CONTEXT})==3
assert c.get(low,length)==expected and word(BODY+28)==3
assert trace==[CLEANUP-h[0]],trace
assert word(TS+12)==2 and word(GEOMETRY_CONTEXT+22)==1 and word(GEOMETRY_CONTEXT+24)==1
unchanged=c.get(low,length);trace.clear()
assert call('world_scene_body_step',{1:BODY,2:GEOMETRY_CONTEXT})==0xfffffffd
assert c.get(low,length)==unchanged and trace==[]
print(json.dumps(dict(status="passed",runs=runs,calls=calls,geometry_cleanup_native_match=True,duplicate_cleanup_rejected=True)))
c.close()
