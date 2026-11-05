#!/usr/bin/env python3
"""Execute command queue with two independently delayed consumers and field cutoffs."""
import random,json
from unicorn_b import *
blob=bytes(BinFmt().load_image(str(build/'input/Gunship.Slave')).get_segments()[0].get_data())
listing=(build/'input/Gunship.lst').read_text(encoding='latin1')
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);Q=0x300000;O=0x310000;rng=random.Random(333);checks=0
size=sym('CQ_SIZE');records=sym('CQ_RECORDS')
def call(name,d0=0,d1=0):
 global checks
 expected={r:rng.randrange(0x1000000) for r in range(1,17) if r not in (8,9)}
 expected.update({1:Q,2:O,10:d1})
 c.rw(8,0x8f000)
 for r,v in expected.items():c.rw(r,v)
 c.rw(9,d0&0xffffffff);c.call(base+sym(name));checks+=1
 assert all(c.rr(r)==v for r,v in expected.items()),name
 assert c.rr(8)==0x8f004 and c.rr(18)==0x90000
 return c.rr(9)
def word(off):return int.from_bytes(c.get(Q+off,2),'big')
def long(off):return int.from_bytes(c.get(Q+off,4),'big')
for epoch in (0,0xfffffff0):
 call('commands_init',epoch)
 c.put(Q,struct.pack('>3H',0xfff0,0xfff0,0xfff0))
 tape=[];read=[0,0]
 for i in range(15000):
  if len(tape)-min(read)<128 and (not tape or rng.randrange(3)==0):
   seq=(epoch+len(tape)+1)&0xffffffff;key=rng.randrange(65536)
   assert call('commands_publish',seq,key)==1;tape.append(struct.pack('>IHH',seq,key,0))
  else:
   role=rng.randrange(2);cutoff=rng.randrange(max(0,len(tape)-10),len(tape)+1)
   expected=read[role]<cutoff
   before=c.get(Q,size)
   assert call('commands_peek',epoch+cutoff,role)==int(expected)
   assert c.get(Q,size)==before
   if expected:
    assert c.get(O,8)==tape[read[role]]
    assert call('commands_peek',epoch+cutoff,role)==1 and c.get(Q,size)==before
    assert call('commands_ack',0,role)==1;read[role]+=1
 for role in (0,1):
  while read[role]<len(tape):
   assert call('commands_pop',epoch+len(tape),role)==1
   assert c.get(O,8)==tape[read[role]];read[role]+=1
  assert call('commands_pop',epoch+len(tape),role)==0
 assert word(0)==word(2)==word(4)
# A fast player may not release slots still needed by the slow world reader.
call('commands_init')
for seq in range(1,129):assert call('commands_publish',seq,seq|0x800)==1
for seq in range(1,129):assert call('commands_pop',128,0)==1
before=c.get(Q+records,size-records)
assert call('commands_publish',129,0x123)==0xffffffff
assert c.get(Q+records,size-records)==before and word(8)==1 and long(16)==1
assert call('commands_pop',128,1)==0xffffffff
assert call('commands_rebase',1000)==128 and long(20)==128
assert word(0)==word(2)==word(4)
assert call('commands_publish',1001,0x123)==1
assert call('commands_pop',1000,0)==0
assert call('commands_pop',1001,0)==1
assert call('commands_pop',1001,1)==1
assert call('commands_pop',1001,2)==0xfffffffe
assert call('commands_pause')==0
before=c.get(Q,size)
assert call('commands_publish',1002,1)==0 and call('commands_pop',1002,1)==0
assert c.get(Q,size)==before
assert call('commands_rebase',2000)==0
assert call('commands_publish',2002,1)==0xffffffff
assert word(8)==1 and long(16)==2
# Hold a mixed command without consuming it while the world reader advances.
call('commands_init')
for seq,key in [(1,3),(2,0x51),(3,3)]:assert call('commands_publish',seq,key)==1
assert call('commands_peek',1,0)==1;held=c.get(O,8);head=word(2)
for seq in range(1,4):assert call('commands_pop',3,1)==1
assert word(2)==head and call('commands_peek',1,0)==1 and c.get(O,8)==held
# Reject altered sequence, key and reserved bits; no cursor moves.
for off in [0,4,6]:
 bad=bytearray(held);bad[off]^=1;c.put(O,bad);before=c.get(Q,size)
 assert call('commands_ack',0,0)==0xfffffffd and c.get(Q,size)==before
c.put(O,held);assert call('commands_ack',0,0)==1
before=c.get(Q,size);assert call('commands_ack',0,0)==0xfffffffd and c.get(Q,size)==before
assert call('commands_peek',1,0)==0 # later command exceeds this field cutoff
assert call('commands_peek',2,0)==1
assert call('commands_ack',0,2)==0xfffffffe
assert call('commands_pause')==0
before=c.get(Q,size);assert call('commands_ack',0,0)==0 and c.get(Q,size)==before
assert call('commands_rebase',100)==2
assert call('commands_publish',101,3)==1
assert call('commands_peek',101,0)==1;c.put(Q+8,struct.pack('>H',1));before=c.get(Q,size)
assert call('commands_ack',0,0)==0xffffffff and c.get(Q,size)==before
report=dict(calls=checks,scope='assembled dual-reader peek/ack plus legacy pop: ordered payloads, field cutoffs, cursor/sequence wrap, overflow, pause/rebase, ABI')
(root/'tmp/c/command-ack-tests.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
