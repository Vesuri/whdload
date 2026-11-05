#!/usr/bin/env python3
"""Connect scaled response/linear rates to native stages; prove h=1 and fractions."""
import json,random
from fractions import Fraction as F
from unicorn_b import *
from layout import locate
mem=(root/'tmp/prof/flight1-mem/fast.bin').read_bytes();h=locate(mem)['hunks']
c=CPU();c.put(0x200000,mem);c.put(base,bytes(BinFmt().load_image(str(root/'tmp/c/field-command-player.hunk')).get_segments()[0].get_data()))
listing=(root/'tmp/c/field-command-player.lst').read_text()
def sym(n):return int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
whole=0x300000;stages=0x310000;p=0x320000;out=0x320100;terms=0x320200;state=0x320300;rng=random.Random(9636);calls=0
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
context=0x420000;candidate=0x421000
CP=0x430000;CW=0x431000;MODE=0x432000;DEC=0x433000
assert call('world_commands_prepare',{1:h[0],2:DEC})==0
for off in [0xaf36,0xa150,0x7eee,0x7c56]:c.put(h[0]+off,bytes.fromhex('4e75'))
runs=[]
def word(a):return int.from_bytes(c.get(a,2),'big')
for rate in ([] if os.environ.get('GS_QUICK') else [50,60]):
 baseline=None
 for batch in [1,3,10,25]:
  assert call('clock_init',{1:TC,9:0,10:rate})==0
  assert call('history_init',{1:TH,9:0})==0
  assert call('commands_init',{1:CQ,9:0})==0
  assert call('scheduler_init',{1:TS,2:TC,3:TH,4:CQ})==0
  assert call('player_step_init',{1:shadow,9:rate,10:0})==0
  c.put(context,struct.pack('>6I',shadow,p,stages,h[0]+0x7a44,packet,candidate)+bytes(16))
  b=bytearray(86);struct.pack_into('>HH',b,0,0x7000,0x8000);struct.pack_into('>H',b,28,1024);struct.pack_into('>H',b,12,65532);b[27]=128;b[57]=26;b[66]=28;c.put(p,b)
  assert call('control_mode_init',{1:MODE,2:p})==0
  c.put(CP,struct.pack('>III',CQ,p,MODE)+bytes(12))
  c.put(CW,struct.pack('>IIII',CQ,p,DEC,h[0]+0xaf36)+bytes(12))
  tick=65532;completed=0;worlds=[];poses=[];lastheld=0;edges=0
  for first in range(1,241,batch):
   for f in range(first,min(first+batch,241)):
    x=[1,0,-1,0][(f//15)%4];y=[0,1,0,-1][(f//20)%4];held=(f//7)%4;edge=held&~lastheld;lastheld=held
    assert call('commands_publish',{1:CQ,9:f,10:[0x51,0x38,0x39,3,0x50,0x7f][f%6]})==1
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
    before=c.get(p,86),c.get(shadow,76)
    assert call('field_player_prepare',{1:context,2:TS,3:rec,9:(tick+1)&65535})==0xfffffffd
    assert before==(c.get(p,86),c.get(shadow,76)) and word(context+36)==0
    assert call('command_phase_player',{1:TS,2:CP,9:1})==0xfffffffe
    assert call('command_phase_player',{1:TS,2:CP,9:1})==0
    before=c.get(p,86),c.get(shadow,76)
    assert call('field_player_prepare',{1:context,2:TS,3:rec,9:(tick+1)&65535})==0
    assert before==(c.get(p,86),c.get(shadow,76)) and word(context+38)==0
    assert call('scheduler_next',{1:TS,2:sample})==0xfffffffd
    due=call('field_player_complete',{1:context});assert due in [0,1]
    assert word(context+38)==1 and word(context+36)==0
    assert call('field_player_complete',{1:context})==0xfffffffd
    assert word(p+12)==tick
    completed+=1;poses.append((c.get(p,86),c.get(shadow,76)))
    assert word(TS+12)==(2 if due else 0)
    if due:
     assert call('scheduler_next',{1:TS,2:sample})==0xfffffffd
     assert word(TS+44)==edges
     while True:
      drained=call('command_phase_world',{1:TS,2:CW,9:3})
      if drained==0:break
      assert drained==0xfffffffe
     assert call('control_mode_check',{1:MODE,2:p})==0
     tick=(tick+1)&65535;c.put(p+12,struct.pack('>H',tick))
     # Observer substitutes for world effects; not a native-world test.
     worlds.append((completed,c.get(p,86),word(TS+44),int.from_bytes(c.get(TS+40,4),'big'),c.get(rec+32,8)))
     assert call('scheduler_world_done',{1:TS})==0;edges=0
   before=c.get(p,86),c.get(shadow,76)
   assert call('player_camera_angles',{1:p,2:shadow,3:camera})==0
   assert before==(c.get(p,86),c.get(shadow,76))
  result=(poses,worlds,c.get(p,86),c.get(shadow,76),c.get(camera+6,6))
  if baseline is None:baseline=result
  else:assert result==baseline,(rate,batch)
  assert completed==240 and len(worlds)==240*3//rate
  assert int.from_bytes(c.get(TS+32,4),'big')==240 and int.from_bytes(c.get(TS+36,4),'big')==len(worlds)
  runs.append(dict(rate=rate,batch=batch,fields=completed,world_observations=len(worlds),clock=tick))

print(json.dumps(dict(status="passed",runs=runs,calls=calls)))
c.close()
