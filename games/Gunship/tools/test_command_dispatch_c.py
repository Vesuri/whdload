"""Native command classification and retained player-reader effects."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/command-dispatch.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/command-dispatch.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
Q=0x300000;P=0x310000;M=0x320000;CTX=0x330000;O=0x340000;REF=0x350000
rng=random.Random(0x4ed4);calls=0
classes={}
for cls,keys in [(1,[0x4c,0x4d,0x4e,0x4f,0x50,0x5a,0x51,0x5b,0x52,0x5c,0x53,0x5d,0x38,0x39,0x3a]),(2,[3]),(3,[1,2,4,5,6,7,8,9,10,11,0x804,0x805,0x806]),(4,[0x45,0x833,0x40,0x1c,0x41,0x37,0x21,0x22,0x34,0x42,0x46])]:
 for key in keys:assert key not in classes;classes[key]=cls
native_keys={int.from_bytes(c.get(h[0]+off+2,2),'big') for off in range(0x4ed4,0x5334,2) if c.get(h[0]+off,2)==bytes.fromhex('0c47')}
assert native_keys==set(classes)|{12} and len(classes)==40

def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(8)==0x8f004 and all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)
keys=list(classes)+[k|0x800 for k in classes]+[rng.randrange(65536) for _ in range(1024)]
for key in keys:assert call('control_command_class',{9:key})==classes.get(key,0)
def setup(flags=16,epoch=0):
 assert call('commands_init',{1:Q,9:epoch})==0
 b=bytearray(86);b[57]=26;b[66]=flags;c.put(P,b);c.put(REF,b)
 assert call('control_mode_init',{1:M,2:P})==0
 c.put(CTX,struct.pack('>III',Q,P,M)+bytes(12))
callback=h[0]+0xaf36;c.put(callback,bytes.fromhex('4e75'))
tapes=[[3,0x51,3,0x50,3,0x52,0x803,0x38,0x4e,0x39,0x4f,0x7f]*3,
       [0x50,0x53,0x5a,0x5c,0x839,3,0x51,0x3a,3,0x5b]*3]
sequences=0
for epoch in [0,0xfffffff0]:
 for batch in [1,3,10,25]:
  for tape in tapes:
   setup(epoch=epoch)
   for n,key in enumerate(tape,1):assert call('commands_publish',{1:Q,9:(epoch+n)&0xffffffff,10:key})==1
   for first in range(0,len(tape),batch):
    stop=min(first+batch,len(tape));cutoff=(epoch+stop)&0xffffffff
    for n in range(first,stop):
     c.rw(6,REF);c.rw(16,tape[n]);c.rw(8,0x8f000);c.call(h[0]+0x4ed4)
     assert call('control_player_next',{1:CTX,9:cutoff})==1
     want=bytearray(c.get(REF,86));want[66]=c.get(P+66,1)[0]
     assert c.get(P,86)==want and c.get(CTX+18,2)==bytes.fromhex('0001')
    assert call('control_player_next',{1:CTX,9:cutoff})==0
    # World reader consumes only its primary effect, never the field tail.
    for n in range(first,stop):
     assert call('commands_pop',{1:Q,2:O,9:cutoff,10:1})==1
     assert call('control_mode_world',{1:P,2:callback,9:tape[n]})==int(tape[n]==3)
    assert c.get(P,86)==c.get(REF,86) and call('control_mode_check',{1:M,2:P})==0
   assert c.get(CTX+20,4)==struct.pack('>I',len(tape));sequences+=1
# Every boundary stays at the retained head, with later controls untouched.
barriers=0
for key,cls in classes.items():
 if cls!=4:continue
 setup();assert call('commands_publish',{1:Q,9:1,10:key})==1;assert call('commands_publish',{1:Q,9:2,10:0x51})==1
 before=c.get(P,86),c.get(M,2),c.get(Q,1048)
 for _ in range(2):assert call('control_player_next',{1:CTX,9:2})==2
 assert before==(c.get(P,86),c.get(M,2),c.get(Q,1048))
 assert c.get(CTX+12,8)==struct.pack('>IHH',1,key,0) and c.get(CTX+20,4)==bytes(4);barriers+=1
# World primaries perform only the yaw tail at field time.
worlds=0
for key,cls in classes.items():
 if cls!=3:continue
 setup();c.put(P+63,bytes([5]));before=bytearray(c.get(P,86));before[63]=4
 assert call('commands_publish',{1:Q,9:1,10:key})==1
 assert call('control_player_next',{1:CTX,9:1})==1 and c.get(P,86)==before
 assert c.get(Q+4,2)==bytes(2);worlds+=1
# Invalid mixed shadow must retain command and not run the tail.
setup();c.put(M,struct.pack('>H',2));c.put(P+63,bytes([5]));assert call('commands_publish',{1:Q,9:1,10:3})==1
before=c.get(P,86),c.get(Q,1048)
assert call('control_player_next',{1:CTX,9:1})==0xffffffff and before==(c.get(P,86),c.get(Q,1048))
assert c.get(CTX+18,6)==bytes(6)
r=dict(classification_cases=len(keys),native_compared_words=len(native_keys),ordered_queue_tapes=sequences,retained_boundaries=barriers,world_primary_tail_cases=worlds,calls=calls,scope='player reader and command ownership; native indicator stubbed; other world effects/modal execution not installed')
(root/'tmp/c/command-dispatch-tests.json').write_text(json.dumps(r,indent=2)+'\n');print(r);c.close()
