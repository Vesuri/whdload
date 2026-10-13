#!/usr/bin/env python3
import sys,json,re,struct,hashlib,argparse
from pathlib import Path

from timing_audit_check import CPU
from cd32_runtime import locate
p=argparse.ArgumentParser(description='Native cannon spawn and prediction-gate reproduction; not timing.')
p.add_argument('build',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[1]
assert not a.output.exists() and (root/'tmp').resolve() in a.output.resolve().parents
memory=(root/'tmp/phase7-combat-controls/start-fast.bin').read_bytes();layout=locate(memory)
build=a.build;blob=(build/'payload.bin').read_bytes()
sy={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)}
S=0x180000;rows=[]
for model in (2,4):
 c=CPU(memory,layout,model);c.write(S,blob)
 def put(n,f,v):c.write(S+sy[n],struct.pack('>'+f,v))
 def run(n):c.run(S+sy[n]-c.code)
 def vec(off,slot):return list(struct.unpack('>3i',c.read(c.data+off+12*slot,12)))
 put('timing_game','I',c.code);put('timing_active','H',1);put('timing_hz','I',50)
 c.data_value(0x3896,'h',0);c.data_value(0xae4,'h',0);c.data_value(0x9564,'h',-1)
 c.data_value(0x9566,'h',-1);c.data_value(0xba54,'h',0)
 c.data_value(0x94c6,'h',-1) # player gun ready, as required by E:06fe
 run('timing_scene_snapshot');run('timing_scene_snapshot')
 player_life_before=c.data_value(0x94c6,'h')
 before=[c.data_value(0x96fe+2*i,'h') for i in range(61)]
 c.run(0xc458,struct.pack('>hh',0,0),end=0xc8ae)
 slot=c.reg(11); row=dict(model=model,slot=slot,old_class=before[slot],new_class=c.data_value(0x96fe+2*slot,'h'),player_life_before=player_life_before,player_life_after=c.data_value(0x94c6,'h'),spawn_position=vec(0x919a,slot),velocity=vec(0x9d6c,slot),life=c.data_value(0x94c6+2*slot,'h'))
 assert row['new_class']==8 and any(row['velocity'])
 c.run(0x76a8,struct.pack('>h',0));c.run(0x76a8,struct.pack('>h',slot))
 row['player_life_at_snapshot']=c.data_value(0x94c6,'h')
 c.run(0x7d1a,struct.pack('>h',slot))
 row['first_world_position']=vec(0x919a,slot)
 assert row['first_world_position']==[a+b for a,b in zip(row['spawn_position'],row['velocity'])]
 run('timing_scene_snapshot');row['spawn_predictable']=c.read(S+sy['timing_scene_predictable']+slot,1)[0]
 assert row['spawn_predictable']==0
 row['player_predictable']=c.read(S+sy['timing_scene_predictable'],1)[0]
 assert row['player_predictable']==0
 c.data_value(0x7f02,'I',100);put('timing_clock','I',100)
 # Independently isolate the new-slot guard and player cooldown guard.
 row['guard_controls']=[]
 authoritative=vec(0x919a,slot)
 for player,projectile in ((0,1),(1,0),(1,1)):
  c.write(S+sy['timing_scene_predictable'],bytes([player]))
  c.write(S+sy['timing_scene_predictable']+slot,bytes([projectile]))
  c.write(S+sy['timing_clock']+4,struct.pack('>I',20))
  run('timing_scene_begin');moved=vec(0x919a,slot)!=authoritative
  assert moved==bool(player and projectile)
  row['guard_controls'].append(dict(player=player,projectile=projectile,moved=moved))
  run('timing_scene_end');assert vec(0x919a,slot)==authoritative
 c.write(S+sy['timing_scene_predictable'],bytes(1))
 c.write(S+sy['timing_scene_predictable']+slot,bytes(1))
 row['renders']=[]
 for tick in (0,1):
  if tick:
   c.run(0x76a8,struct.pack('>h',0));c.run(0x76a8,struct.pack('>h',slot))
   c.run(0x7d1a,struct.pack('>h',slot));run('timing_scene_snapshot')
  mask=c.read(S+sy['timing_scene_predictable']+slot,1)[0]
  assert mask==tick
  authoritative=vec(0x919a,slot)
  for debt in (0,10,20,30,40):
   c.write(S+sy['timing_clock']+4,struct.pack('>I',debt))
   run('timing_scene_begin');position=vec(0x919a,slot)
   fraction=int.from_bytes(c.read(S+sy['timing_scene_fraction'],4),'big')
   row['renders'].append(dict(tick=tick,debt=debt,fraction=fraction,predictable=mask,position=position))
   if not tick:assert position==authoritative
   else:assert position!=authoritative
   run('timing_scene_end');assert vec(0x919a,slot)==authoritative
 rows.append(row);c.close()
a.output.write_text(json.dumps(dict(memory_sha256=hashlib.sha256(memory).hexdigest(),payload_sha256=hashlib.sha256(blob).hexdigest(),cases=rows),indent=2)+'\n')
print('PASS: native spawn, first integration, two independent prediction guards and 20 render samples')
