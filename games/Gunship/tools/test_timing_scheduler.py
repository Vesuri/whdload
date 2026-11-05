#!/usr/bin/env python3
"""Execute field/player/world coordinator with bounded batches and strict acknowledgements."""
import json,random
from unicorn_b import *
blob=bytes(BinFmt().load_image(str(root/'tmp/c/scheduler.bin')).get_segments()[0].get_data())
listing=(root/'tmp/c/scheduler.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);T=0x300000;H=0x310000;Q=0x320000;S=0x330000;R=0x340000;O=0x350000
rng=random.Random(33);checks=0
BAD=0xffffffff;PHASE=0xfffffffd;BOUND=0xfffffffe
def call(name,d0=0,d1=0,a0=S,a1=O):
 global checks
 expected={r:rng.randrange(0x1000000) for r in range(1,17) if r not in (8,9)}
 expected.update({1:a0,2:a1,3:H,4:Q,10:d1});c.rw(8,0x8f000)
 for r,v in expected.items():c.rw(r,v)
 c.rw(9,d0&0xffffffff);c.call(base+sym(name));checks+=1
 assert all(c.rr(r)==v for r,v in expected.items()),name
 assert c.rr(8)==0x8f004 and c.rr(18)==0x90000
 return c.rr(9)
def init(rate=50,epoch=0):
 assert call('clock_init',epoch,rate,a0=T)==0
 assert call('history_init',epoch,a0=H)==0
 assert call('commands_init',a0=Q)==0
 assert call('scheduler_init',a1=T)==0
 return epoch
def publish(f):
 c.put(R,struct.pack('>10I',f&0xffffffff,1,2,3,4,0,6,7,(f*17)&0xffffffff,(f*31)&0xffffffff))
 assert call('history_publish',a0=H,a1=R)==1
schedules=[]
for rate in (50,60):
 for batch in (1,10,25):
  epoch=0xfffffff0;init(rate,epoch);world=[];fields=[]
  for start in range(0,300,batch):
   for n in range(start+1,min(start+batch,300)+1):publish(epoch+n)
   assert call('scheduler_begin',128,8)==0
   while True:
    status=call('scheduler_next')
    if status==0:break
    assert status==1,status
    stamp=int.from_bytes(c.get(O,4),'big');fields.append(stamp)
    assert call('scheduler_next')==PHASE
    assert call('scheduler_world_done')==PHASE
    assert call('scheduler_begin',128,8)==PHASE
    due=call('scheduler_player_done')
    n=(stamp-epoch)&0xffffffff
    assert due==(3*n//rate-3*(n-1)//rate)
    if due:
     assert call('scheduler_next')==PHASE
     assert call('scheduler_player_done')==PHASE
     world.append(stamp);assert call('scheduler_world_done')==0
   assert len(fields)==min(start+batch,300)
  assert fields==[(epoch+n)&0xffffffff for n in range(1,301)]
  assert int.from_bytes(c.get(S+sym('TS_STEPS'),4),'big')==300
  assert int.from_bytes(c.get(S+sym('TS_WORLDS'),4),'big')==900//rate
  schedules.append(dict(rate=rate,batch=batch,world=world))
# A producer arriving after begin belongs to the next batch.
init();publish(1);assert call('scheduler_begin',128,8)==0;publish(2)
assert call('scheduler_next')==1;assert call('scheduler_player_done')==0
assert call('scheduler_next')==0
assert call('scheduler_begin',128,8)==0
assert call('scheduler_next')==1;assert int.from_bytes(c.get(O,4),'big')==2
assert call('scheduler_player_done')==0;assert call('scheduler_next')==0
# Catch-up cannot renew its own tick budget while an old batch is incomplete.
init()
for n in range(1,101):publish(n)
assert call('scheduler_begin',128,3)==0
for n in range(1,67):
 assert call('scheduler_next')==1
 if call('scheduler_player_done'):assert call('scheduler_world_done')==0
assert call('scheduler_next')==BOUND
assert int.from_bytes(c.get(T,4),'big')==66
assert int.from_bytes(c.get(H+2,2),'big')==66
assert call('scheduler_begin',128,3)==PHASE
# Field bound also requires explicit recovery rather than silently dropping debt.
init()
for n in range(1,21):publish(n)
assert call('scheduler_begin',10,3)==0
for _ in range(10):assert call('scheduler_next')==1;assert call('scheduler_player_done')==0
assert call('scheduler_next')==BOUND and call('scheduler_begin',10,3)==PHASE
# Each upstream fault/inactive state latches; clearing it alone cannot resume.
for owner,offset,value in [(T,26,1),(H,6,1),(Q,8,1),(T,24,0),(H,4,0),(Q,6,0)]:
 init();publish(1);assert call('scheduler_begin',128,3)==0
 c.put(owner+offset,struct.pack('>H',value));assert call('scheduler_next')==BAD
 c.put(owner+offset,struct.pack('>H',1-value));assert call('scheduler_next')==BAD
 assert c.get(H+2,2)==bytes(2)
# Argument errors must leave state untouched.
for f,t in [(0,3),(129,3),(10,0),(10,9),(0xffffffff,3)]:
 init();before=c.get(S,sym('TS_SIZE'));assert call('scheduler_begin',f,t)==PHASE
 assert c.get(S,sym('TS_SIZE'))==before
# Completed work remains counted when a producer faults while it runs.
init();publish(1);assert call('scheduler_begin',128,3)==0
assert call('scheduler_next')==1;c.put(Q+8,b'\0\1')
assert call('scheduler_player_done')==BAD
assert int.from_bytes(c.get(S+32,4),'big')==1
assert call('scheduler_player_done')==PHASE
assert call('scheduler_next')==BAD
# Explicit coordinated rebase recovers without resetting lifetime completions.
assert call('history_rebase',1000,a0=H)==0
assert call('clock_rebase',1000,a0=T)==3
assert call('commands_rebase',0,a0=Q)==0
assert call('scheduler_rebase')==0
assert int.from_bytes(c.get(S+32,4),'big')==1
publish(1001);assert call('scheduler_begin',128,3)==0
assert call('scheduler_next')==1;assert call('scheduler_player_done')==0
assert int.from_bytes(c.get(S+32,4),'big')==2
init()
for n in range(1,18):publish(n)
assert call('scheduler_begin',128,3)==0
for n in range(1,18):
 assert call('scheduler_next')==1
 assert call('scheduler_player_done')==(n==17)
c.put(Q+8,b'\0\1')
assert call('scheduler_world_done')==BAD
assert int.from_bytes(c.get(S+36,4),'big')==1
assert call('scheduler_world_done')==PHASE
assert call('scheduler_next')==BAD
# A short press early in the interval survives until the world deadline.
init()
for n in range(1,18):
 c.put(R,struct.pack('>8I',n,0,0,1 if n==1 else 0,0,0,0,1 if n==1 else 0))
 assert call('history_publish',a0=H,a1=R)==1
assert call('scheduler_begin',128,3)==0
for n in range(1,18):
 assert call('scheduler_next')==1
 assert call('scheduler_player_done')==(n==17)
assert int.from_bytes(c.get(S+sym('TS_EDGES'),2),'big')==1
assert int.from_bytes(c.get(S+sym('TS_HELD'),4),'big')==0
assert call('scheduler_world_done')==0
assert c.get(S+sym('TS_EDGES'),2)==bytes(2)
report=dict(calls=checks,schedules=schedules,scope='assembled coordinator only; no native scheduling or player integrator claim')
(root/'tmp/c/scheduler-tests.json').write_text(json.dumps(report,indent=2)+'\n');print(dict(calls=checks,schedules=len(schedules)));c.close()
