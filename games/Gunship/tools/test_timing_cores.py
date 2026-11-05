#!/usr/bin/env python3
"""Execute standalone assembled clock/history code with sequential composition tests."""
import json,random,hashlib
from unicorn_b import *
from collections import deque
rng=random.Random(1650)
blob=bytes(BinFmt().load_image(str(root/'tmp/c/cores.bin')).get_segments()[0].get_data())
listing=(root/'tmp/c/cores.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
S=0x300000;H=0x310000;R=0x320000;O=0x330000
c=CPU();c.put(base,blob)
checks=0
def invoke(n,a=S,d0=0,d1=0,a1=R):
 global checks
 c.rw(8,0x8f000)
 expected={r:rng.randrange(0x10000000) for r in range(1,17) if r not in (8,9)}
 expected.update({1:a,2:a1,10:d1})
 for r,v in expected.items():c.rw(r,v)
 c.rw(9,d0);c.call(base+sym(n))
 assert c.rr(18)==0x90000,(n,hex(c.rr(18)))
 assert c.rr(8)==0x8f004
 assert all(c.rr(r)==v for r,v in expected.items()),n
 checks+=1
 return c.rr(9)
def w(a):return int.from_bytes(c.get(a,2),'big')
def l(a):return int.from_bytes(c.get(a,4),'big')
def sample(f):return struct.pack('>I',f)+rng.randbytes(36)
for rate in (50,60):
 for epoch in (0,0xfffffff0):
  assert invoke('clock_init',d0=epoch,d1=rate)==0
  due=[]
  for n in range(1,rate*120+1):
   result=invoke('clock_field',d0=(epoch+n)&0xffffffff)
   assert result==(3*n//rate-3*(n-1)//rate)
   if result:due.append(n)
   assert w(S+sym('TC_PHASE'))==3*n%rate
  assert len(due)==360
  assert [due[0]]+[b-a for a,b in zip(due,due[1:3])]==([17,17,16] if rate==50 else [20,20,20])
  prior=c.get(S,sym('TC_STATE_SIZE'))
  assert invoke('clock_init',d0=1,d1=49)==0xffffffff
  assert c.get(S,sym('TC_STATE_SIZE'))==prior
  # Duplicate, gap, negative ordering cannot advance the clock or self-recover.
  assert invoke('clock_field',d0=(epoch+rate*120)&0xffffffff)==0xffffffff
  assert invoke('clock_field',d0=(epoch+rate*120+1)&0xffffffff)==0xffffffff
  assert invoke('clock_rebase',d0=30000)==0
  assert invoke('clock_field',d0=30001)==0
  assert invoke('clock_pause')==0
  prior=c.get(S,sym('TC_STATE_SIZE'))
  assert invoke('clock_field',d0=30100)==0xfffffffe
  assert c.get(S,sym('TC_STATE_SIZE'))==prior
  assert invoke('clock_rebase',d0=40000)==3
  assert l(S+sym('TC_DROPPED'))==3
# Full ring preserves unread bytes and stamps, faults until explicit recovery.
assert invoke('history_init',a=H,d0=0xfffffff0)==0
queue=[]
for n in range(1,129):
 b=sample((0xfffffff0+n)&0xffffffff);queue.append(b);c.put(R,b)
 assert invoke('history_publish',a=H)==1
saved=c.get(H+20,5120)
c.put(R,sample(113));assert invoke('history_publish',a=H)==0xffffffff
assert c.get(H+20,5120)==saved
assert invoke('history_pop',a=H,a1=O)==0xffffffff
assert invoke('history_publish',a=H)==0xffffffff
assert l(H+8)==2 and w(H+2)==0
assert invoke('history_rebase',a=H,d0=1000)==128
assert l(H+12)==128
assert invoke('history_pop',a=H,a1=O)==0
# Random producer/consumer bursts and cursor wrap; compare every payload byte.
queue=deque();field=1000
for _ in range(70000):
 if not queue or (len(queue)<120 and rng.randrange(2)):
  field+=1;b=sample(field);c.put(R,b);queue.append(b)
  assert invoke('history_publish',a=H)==1
 else:
  assert invoke('history_pop',a=H,a1=O)==1
  assert c.get(O,40)==queue.popleft()
while queue:
 assert invoke('history_pop',a=H,a1=O)==1
 assert c.get(O,40)==queue.popleft()
# Force cursor rollover rather than relying on random operation count.
c.put(H,struct.pack('>HH',65535,65535))
field+=1;c.put(R,sample(field));assert invoke('history_publish',a=H)==1
assert w(H)==0 and w(H+2)==65535
assert invoke('history_pop',a=H,a1=O)==1 and w(H+2)==0
assert invoke('history_pause',a=H)==0
saved=c.get(H,sym('TH_SIZE'))
assert invoke('history_publish',a=H)==0 and invoke('history_pop',a=H)==0
assert c.get(H,sym('TH_SIZE'))==saved
assert invoke('history_rebase',a=H,d0=200000)==0
c.put(R,sample(200002));assert invoke('history_publish',a=H)==0xffffffff
assert w(H)==w(H+2) and w(H+6)==1
# Same field tape, different render batches: player order and world intervals identical.
results=[]
for rate in (50,60):
 for batch in (1,3,10,25):
  invoke('clock_init',d0=0,d1=rate);invoke('history_init',a=H,d0=0)
  frames=[];world=[];edges=0
  for start in range(0,600,batch):
   for f in range(start+1,min(start+batch,600)+1):
    b=struct.pack('>7IH',f,f^0x100,0xffffffff,f%3,f*2,f*3,0,0)+struct.pack('>H',1 if f%11==0 else 0)
    c.put(R,b);assert invoke('history_publish',a=H)==1
   while invoke('history_pop',a=H,a1=O)==1:
    b=c.get(O,40);f=int.from_bytes(b[:4],'big');frames.append(f)
    edges |= int.from_bytes(b[30:32],'big')
    if invoke('clock_field',d0=f):world.append((f,edges));edges=0
  assert frames==list(range(1,601))
  if batch==1:reference=world
  else:assert world==reference
  results.append(dict(rate=rate,batch=batch,ticks=len(world),remainder=w(S+20)))
c.close()
report=dict(calls=checks,schedules=results,code_sha256=hashlib.sha256(blob).hexdigest(),scope='assembled clock and ring cores; no native adapter or live flight claim')
(root/'tmp/c/core-tests.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
