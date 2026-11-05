"""Paused lifecycle completion marking and independent reader retirement."""
from unicorn_b import *
import random,json,itertools
blob=bytes(BinFmt().load_image(str(root/'tmp/c/runtime.hunk')).get_segments()[0].get_data());listing=(root/'tmp/c/runtime.lst').read_text()
def addr(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
c=CPU();c.put(base,blob);Q=0x300000;CP=0x310000;CW=0x320000;P=0x330000;MODE=0x340000;RECORD=0x350000;rng=random.Random(45);calls=0
keys=(0x45,0x833,12,0x40,0x1c,0x41,0x37,0x21,0x22,0x34,0x42,0x46)
def call(name,args,want):
 global calls
 rs={r:rng.randrange(0x1000000) for r in range(1,17) if r!=8};rs.update(args)
 for r,v in rs.items():c.rw(r,v&0xffffffff)
 c.rw(8,0x8f000);c.call(addr(name));calls+=1
 assert c.rr(8)==0x8f004 and c.rr(9)==want,(name,c.rr(9),want)
 assert all(c.rr(r)==v&0xffffffff for r,v in rs.items() if r!=9),name

def setup(key,start=0,lag=0,epoch=0):
 player=(start+lag)&65535;write=(player+1)&65535;cutoff=(epoch+lag+1)&0xffffffff
 c.put(Q,struct.pack('>4H4I',write,player,start,1,0,cutoff,0,0)+bytes(1024))
 for n in range(lag+1):
  c.put(Q+24+((start+n)&127)*8,struct.pack('>IHH',(epoch+n+1)&0xffffffff,key if n==lag else 0,0))
 c.put(CP,struct.pack('>3I',Q,P,MODE)+bytes(12));c.put(CW,struct.pack('>4I',Q,P,0,0)+bytes(12))
 c.put(P,b'\x33'*86);c.put(RECORD,struct.pack('>IHH',cutoff,key,0));return cutoff,player,Q+24+(player&127)*8
cases=0
for key,start,lag,epoch in itertools.product(keys,(0,127,65535),(0,3,127),(0,0xfffffffe)):
 cutoff,player,slot=setup(key,start,lag,epoch);before=c.get(P,86)
 call('control_player_next',{1:CP,9:cutoff},2);assert c.get(P,86)==before
 call('commands_pause',{1:Q},0);snapshot=bytearray(c.get(Q,1048));snapshot[slot-Q+6:slot-Q+8]=b'\0\1'
 call('boundary_command_mark',{1:Q,2:RECORD},1);assert c.get(Q,1048)==snapshot and c.get(RECORD+6,2)==bytes(2)
 call('boundary_command_mark',{1:Q,2:RECORD},0xfffffffd);assert c.get(Q,1048)==snapshot
 c.put(Q+6,b'\0\1')
 call('control_player_next',{1:CP,9:cutoff},1);assert c.get(P,86)==before
 assert int.from_bytes(c.get(Q+2,2),'big')==(player+1)&65535
 for n in range(lag+1):call('control_world_next',{1:CW,9:cutoff},1)
 assert c.get(P,86)==before and c.get(Q+2,2)==c.get(Q+4,2)==c.get(Q,2)
 call('control_player_next',{1:CP,9:cutoff},0);call('control_world_next',{1:CW,9:cutoff},0)
 cases+=1
# Rejected mark calls leave the queue and private record byte-identical.
rejects=0
for change in ('active','fault','empty','too_full','world_ahead','lag_overflow','sequence','key','flags','not_boundary'):
 cutoff,player,slot=setup(0x42);c.put(Q+6,bytes(2))
 if change=='active':c.put(Q+6,b'\0\1')
 if change=='fault':c.put(Q+8,b'\0\1')
 if change=='empty':c.put(Q,bytes(2))
 if change=='too_full':c.put(Q,b'\0\x81')
 if change=='world_ahead':c.put(Q+4,b'\0\1')
 if change=='lag_overflow':c.put(Q+4,b'\xff\x80')
 if change=='sequence':c.put(RECORD,b'\0\0\0\2')
 if change=='key':c.put(RECORD+4,b'\0\x40')
 if change=='flags':c.put(RECORD+6,b'\0\1')
 if change=='not_boundary':c.put(RECORD+4,b'\0\x51');c.put(slot+4,b'\0\x51')
 before=c.get(Q,1048),c.get(RECORD,8);call('boundary_command_mark',{1:Q,2:RECORD},0xfffffffd)
 assert (c.get(Q,1048),c.get(RECORD,8))==before;rejects+=1
# Invalid completion flags cannot suppress an ordinary primary or advance cursors.
for key,flags in ((0x51,1),(1,1),(3,1),(0,1),(0x42,2),(0x42,65535)):
 cutoff,player,slot=setup(key);c.put(slot+6,struct.pack('>H',flags));before=c.get(Q,1048),c.get(P,86)
 for reader,context in [('control_player_next',CP),('control_world_next',CW)]:
  call(reader,{1:context,9:cutoff},0xfffffffd);assert (c.get(Q,1048),c.get(P,86))==before
print(json.dumps(dict(status='passed',retirement_cases=cases,calls=calls,atomic_rejections=rejects,invalid_flag_cases=12)));c.close()
