"""Native command classification and retained player-reader effects."""
import json,random
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/command-phase.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/command-phase.lst').read_text()
def sym(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
Q=0x300000;P=0x310000;M=0x320000;CTX=0x330000;O=0x340000;REF=0x350000
clone=0x360000;WCTX=0x370000
rng=random.Random(0x4ed4);calls=0
classes={}
for cls,keys in [(1,[0x4c,0x4d,0x4e,0x4f,0x50,0x5a,0x51,0x5b,0x52,0x5c,0x53,0x5d,0x38,0x39,0x3a]),(2,[3]),(3,[1,2,4,5,6,7,8,9,10,11,0x804,0x805,0x806]),(4,[0x45,0x833,0xc,0x40,0x1c,0x41,0x37,0x21,0x22,0x34,0x42,0x46])]:
 for key in keys:assert key not in classes;classes[key]=cls
native_keys={int.from_bytes(c.get(h[0]+off+2,2),'big') for off in range(0x4ed4,0x5334,2) if c.get(h[0]+off,2)==bytes.fromhex('0c47')}
assert native_keys==set(classes) and len(classes)==41

def call(name,args):
 global calls
 regs={r:rng.randrange(0x1000000) for r in range(1,17) if r not in [8,9]};regs.update(args)
 for r,v in regs.items():c.rw(r,v)
 c.rw(8,0x8f000);c.call(sym(name));calls+=1
 assert c.rr(8)==0x8f004 and all(c.rr(r)==v for r,v in regs.items() if r!=9),name
 return c.rr(9)

T=0x380000;CLK=0x390000;HIST=0x3a0000
assert call('world_commands_prepare',{1:h[0],2:clone})==0
for off in [0xaf36,0xa150,0x7eee,0x7c56]:c.put(h[0]+off,bytes.fromhex('4e75'))
def setup(epoch=0):
 assert call('commands_init',{1:Q,9:epoch})==0
 b=bytearray(86);b[57]=26;b[66]=16;c.put(P,b)
 assert call('control_mode_init',{1:M,2:P})==0
 c.put(CTX,struct.pack('>III',Q,P,M)+bytes(12))
 c.put(WCTX,struct.pack('>4I',Q,P,clone,h[0]+0xaf36)+bytes(12))
 c.put(CLK,bytes(28));c.put(CLK+24,b'\0\1')
 c.put(HIST,bytes(5140));c.put(HIST+4,b'\0\1')
 assert call('scheduler_init',{1:T,2:CLK,3:HIST,4:Q})==0
 c.put(T+12,struct.pack('>HHHH',1,1,0,1))
def phase(name,ctx,budget):return call('command_phase_'+name,{1:T,2:ctx,9:budget})
cases=0
for epoch in [0,0xfffffff0]:
 for budget in [1,3,10,128]:
  setup(epoch);c.put(P+4,b'\x10\x00')
  tape=[1,2,3,0x51,3,0x50,0x38,0x39]*3
  for n,key in enumerate(tape,1):assert call('commands_publish',{1:Q,9:(epoch+n)&0xffffffff,10:key})==1
  c.put(T+28,struct.pack('>I',(epoch+18)&0xffffffff))
  before=c.get(P,86),c.get(Q,1048)
  assert phase('world_before_player',WCTX,budget)==0xfffffffd
  assert before==(c.get(P,86),c.get(Q,1048))
  while phase('player',CTX,budget)==0xfffffffe:pass
  while True:
   result=phase('world_before_player',WCTX,budget)
   if result==0:break
   assert result==0xfffffffe
  assert int.from_bytes(c.get(Q+4,2),'big')==18 and c.get(T+12,2)==b'\0\1'
  assert c.get(T+32,8)==bytes(8)
  assert call('control_mode_check',{1:M,2:P})==0
  before=c.get(P,86),c.get(Q,1048),c.get(WCTX,28)
  assert phase('world_before_player',WCTX,budget)==0
  # A no-work drain resets COMMITTED but applies no further primary effects.
  assert before[:2]==(c.get(P,86),c.get(Q,1048))
  applied=c.get(WCTX+24,4)
  assert call('scheduler_player_done',{1:T})==1
  assert phase('world',WCTX,budget)==0 and c.get(WCTX+24,4)==applied
  assert call('scheduler_world_done',{1:T})==0
  cases+=1
for kind in ['not-due','ready','world','fault','budget0','budget129','queue']:
 setup();c.put(T+28,struct.pack('>I',1));assert call('commands_publish',{1:Q,9:1,10:1})==1
 assert phase('player',CTX,4)==0
 if kind=='not-due':c.put(T+14,bytes(2))
 if kind=='ready':c.put(T+12,bytes(2))
 if kind=='world':c.put(T+12,b'\0\2')
 if kind=='fault':c.put(HIST+6,b'\0\1')
 if kind=='queue':c.put(WCTX,struct.pack('>I',Q+8))
 before=c.get(P,86),c.get(Q,1048)
 got=phase('world_before_player',WCTX,0 if kind=='budget0' else 129 if kind=='budget129' else 4)
 assert got==(0xffffffff if kind=='fault' else 0xfffffffd),(kind,hex(got))
 assert before==(c.get(P,86),c.get(Q,1048))
 cases+=1
print(dict(cases=cases,calls=calls))
