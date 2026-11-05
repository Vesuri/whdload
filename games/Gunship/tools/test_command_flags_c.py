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
 c.put(0x90000,bytes.fromhex('40f9003f0000'))
 c.rw(9,d0&0xffffffff);c.call(base+sym(name),end=0x90006);checks+=1
 result=c.rr(9);flags=int.from_bytes(c.get(0x3f0000,2),'big')&15
 assert flags==(8 if result&0x80000000 else 4 if result==0 else 0),(name,hex(result),flags)
 assert all(c.rr(r)==v for r,v in expected.items()),name
 assert c.rr(8)==0x8f004 and c.rr(18)==0x90006
 return c.rr(9)
def word(off):return int.from_bytes(c.get(Q+off,2),'big')
def long(off):return int.from_bytes(c.get(Q+off,4),'big')
for n in range(256):
 assert call('commands_init')==0
 assert call('commands_publish',1,n)==1
 assert call('commands_peek',1,0)==1
 assert call('commands_ack',0,0)==1
 assert call('commands_pop',1,1)==1
 assert call('commands_pop',1,0)==0
 assert call('commands_peek',1,0)==0
 assert call('commands_ack',0,2)==0xfffffffe
 c.put(Q+8,struct.pack('>H',1))
 for name in ['commands_peek','commands_pop','commands_ack']:assert call(name,1,0)==0xffffffff
report=dict(calls=checks,scope='native result NZVC plus register preservation for pop/peek/ack, publish/init, empty/invalid/fault paths')
(root/'tmp/c/command-flags-tests.json').write_text(json.dumps(report,indent=2)+'\n');print(report);c.close()
