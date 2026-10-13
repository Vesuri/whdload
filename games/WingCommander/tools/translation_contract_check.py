#!/usr/bin/env python3
"""C2 signed carry, native fallbacks, render isolation and diagnostic controls."""
import argparse,json,re,struct,random
from pathlib import Path
from timing_audit_check import CPU
from cd32_runtime import ROOT,locate
from translation_check import S,POS,VEL,trunc,vec

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:p.error('fresh tmp output required')
 memory=(ROOT/'tmp/phase7-combat-controls/start-fast.bin').read_bytes();layout=locate(memory);blob=(a.build/'payload.bin').read_bytes()
 sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
 arithmetic=0;fallbacks=0;renders=0
 for model in (2,4):
  def setup():
   c=CPU(memory,layout,model);c.write(S,blob);c.write(S+sy['timing_game'],struct.pack('>I',c.code))
   for label in ('timing_active','timing_in_world','translation_active'):c.write(S+sy[label],b'\0\1')
   c.data_value(0x3896,'h',0);c.data_value(0xae4,'h',0);c.data_value(0x9564,'h',-1);c.data_value(0x96fe,'h',12)
   for off,label in ((0x807a,'translation_velocity'),(0x80b6,'translation_position')):c.write(c.code+off,struct.pack('>HI',0x4ef9,S+sy[label]))
   return c
  c=setup();rng=random.Random(2)
  for hz in (50,60):
   for value in [-2**31,-51,-1,0,1,51,2**31-1]+[rng.randint(-2**31,2**31-1) for _ in range(100)]:
    for remainder in (-hz+1,0,hz-1):
     address=S+sy['translation_remainders'];c.write(address,struct.pack('>i',remainder))
     c.run(S+sy['translation_fraction']-c.code,registers={1:address,9:value&0xffffffff,16:hz})
     expected=trunc(value*10+remainder,hz);got=struct.unpack('>i',struct.pack('>I',c.reg(9)))[0]
     assert got==expected and c.read(address,4)==struct.pack('>i',value*10+remainder-expected*hz)
     arithmetic+=1
  c.write(S+sy['translation_remainders'],struct.pack('>6i',1,-2,3,-4,5,-6))
  c.run(S+sy['translation_reset']-c.code)
  assert c.read(S+sy['translation_active'],2)==bytes(2) and c.read(S+sy['translation_remainders'],24)==bytes(24)
  # Bypass the scaler in a private CPU copy: the arithmetic oracle must reject it.
  c.write(S+sy['translation_fraction'],b'\x4e\x75')
  c.run(S+sy['translation_fraction']-c.code,registers={1:S+sy['translation_remainders'],9:5120,16:50})
  assert c.reg(9)!=trunc(5120*10,50),'disabled-scaler sabotage was missed'
  c.close()
  for mode in ('npc','inactive','native-call','external','script','action'):
   c=setup();ref=CPU(memory,layout,model);slot=1 if mode=='npc' else 0
   if mode=='inactive':c.write(S+sy['translation_active'],bytes(2))
   if mode=='native-call':c.write(S+sy['timing_in_world'],bytes(2))
   if mode=='external':c.data_value(0x3896,'h',8)
   if mode=='script':c.data_value(0xae4,'h',1)
   if mode=='action':c.data_value(0x9564,'h',4)
   ref.write(ref.data,c.read(c.data,0xfda0))
   for q in (c,ref):q.run(0x7d1a,struct.pack('>h',slot))
   assert c.read(c.data,0xfda0)==ref.read(ref.data,0xfda0),mode
   c.close();ref.close();fallbacks+=1
  for hz in (50,60):
   c=setup();c.write(S+sy['timing_hz'],struct.pack('>I',hz));c.write(S+sy['timing_clock'],struct.pack('>II',100,20));c.data_value(0x7f02,'I',100)
   def own(label):c.run(S+sy[label]-c.code)
   own('timing_scene_snapshot');own('timing_scene_snapshot');own('translation_field');own('timing_player_camera')
   before=c.read(c.data,0xfda0);position=vec(c,POS);velocity=vec(c,VEL)
   own('timing_scene_begin')
   assert vec(c,POS)==tuple(x+trunc(v*10,hz) for x,v in zip(position,velocity)), 'player double prediction or skipped field pose'
   own('timing_scene_end');assert c.read(c.data,0xfda0)==before,'renderer leaked future pose'
   if 'translation_tick_begin' in sy:
    own('translation_tick_begin');own('translation_tick_end')
    assert int.from_bytes(c.read(S+sy['translation_ticks_checked'],4),'big')==1
    assert c.read(S+sy['translation_position_corrections'],8)==bytes(8)
    own('translation_tick_begin');c.data_value(POS,'i',c.data_value(POS,'i')+1);c.data_value(POS+61*12,'i',c.data_value(POS+61*12,'i')+1);own('translation_tick_end')
    assert c.read(S+sy['translation_position_corrections'],8)==struct.pack('>II',1,1),'tick correction sabotage was missed'
   c.close();renders+=1
 a.output.write_text(json.dumps(dict(arithmetic_cases=arithmetic,reset_cases=2,disabled_scaler_negative_controls=2,native_fallbacks=fallbacks,render_isolation_cases=renders,diagnostic_negative_controls='translation_tick_begin' in sy),indent=2)+'\n');print(a.output.read_text())
if __name__=='__main__':main()
