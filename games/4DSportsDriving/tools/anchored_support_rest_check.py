#!/usr/bin/env python3
"""Check acquired zero-band resting configurations without changing their pose."""
import json
from pathlib import Path
from copy import deepcopy
from native_contact_response import rotate,sine,word
from crest_terrain_query import query
from supported_plane_model import geometry,dot
from anchored_support_model import solve,project
from contact_step import step
root=Path('tmp/prof');r=json.loads((root/'native20-contact-model/prediction.json').read_text())['records'];canonical={v['tick']:v for v in json.loads((root/'natural-crest20/bridge.json').read_text())['rows']}
checked=[];excluded=0
for observed in r['ENTRY']:
 if any(observed[13:41]):continue
 e=observed.copy();pitch=e[2];m=[16384,0,0,0,sine(pitch+256),-sine(pitch),0,sine(pitch),sine(pitch+256)]
 pos=[canonical[e[0]-1][a] for a in ('x','y','z')];world=[[p+v for p,v in zip(pos,rotate([x,-384,z],m))] for x,z in ((-960,1984),(960,1984),(960,-1984),(-960,-1984))]
 cached=[[v>>6 for v in xyz] for xyz in world];rows=[query(xyz,ca) for xyz,ca in zip(world,cached)]
 if any(row['clearance']!=0 for row in rows):excluded+=1;continue
 support=[]
 for xyz,row in zip(world,rows):
  origin=[row['origin_'+a] for a in 'xyz'];normal=[row['normal_'+a] for a in 'xyz'];target=dot(xyz,origin,normal)
  out,res=project(xyz,origin,normal,target);assert out==xyz and res==0
  support.append(dict(surface=geometry(row),target=target))
 state=dict(entry=e,position=pos,cached=cached,anchored_support=support);initial=deepcopy(state)
 for _ in range(100):
  state,record=step(state,50,0,body_solver=solve)
  assert state['position']==pos and state['entry'][1:4]==initial['entry'][1:4]
  assert state['entry'][13:45]==initial['entry'][13:45]
  assert state['anchored_support']==support
 checked.append(dict(seed_tick=observed[0],pitch=pitch,target_depths=[x['target'] for x in support]))
report=dict(resting_states=len(checked),updates=100*len(checked),excluded_nonzero_initial_query=excluded,failures=[],states=checked,
 scope='100 zero-distance50Hz steps from each zero-gravity/zero-extension/native-queryzero recorded pose, support explicitly acquired at that pose. Position, orientation, wheel state, carries and support target remain unchanged. No moving-contact, release, impact or full handling acceptance.')
(root/'anchored-support-rest-check.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items() if k not in ('states','scope')})
