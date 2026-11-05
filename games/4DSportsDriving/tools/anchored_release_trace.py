#!/usr/bin/env python3
"""Trace support loss and surface crossing including body-rebuild movement."""
import json,struct
from fractions import Fraction
from copy import deepcopy
from pathlib import Path
from contact_step import step
from anchored_support_model import solve
from crest_terrain_query import query
from supported_plane_model import geometry,dot
root=Path('tmp/prof');cap=root/'contact-prediction-d9';r=json.loads((cap/'prediction.json').read_text())['records'];meta=json.loads((cap/'anchor.json').read_text());mem=(cap/'memory.bin').read_bytes();car=meta['data_base']+0x7ffe-0x92e-meta['memory_base']
canon={v['tick']:v for v in json.loads((root/'crest-d9e7903/bridge.json').read_text())['rows']}
state=dict(entry=r['ENTRY'][0].copy(),position=[canon[450][a] for a in ('x','y','z')],cached=[list(struct.unpack_from('>3h',mem,car+0x74+6*w)) for w in range(4)])
selected={(v['tick'],v['wheel']):v for v in r['SELECT']};events=[];previous=None
for observed in r['ENTRY']:
 t=observed[0];before=deepcopy(state);state,record=step(state,50,selected[t,0]['distance'],body_solver=solve)
 for w,row in enumerate(record['selected']):
  old=[row['old_world_'+a] for a in 'xyz'];new=[row['world_'+a] for a in 'xyz'];oldquery=query(old,before['cached'][w]);oldkey=geometry(oldquery);newkey=geometry(row)
  support=before.get('anchored_support',[None]*4)[w];ending=state['anchored_support'][w];out=record['output']['wheels'][w]
  changed=oldkey!=newkey;lost=support is not None and ending is None
  if not changed and not lost:continue
  ev=dict(tick=t,wheel=w,old_plane=oldquery['plane'],new_plane=row['plane'],surface_change=changed,support_lost=lost,had_support=support is not None,
    branch=out['branch'],old_world=old,translated_world=new,velocity_fifths=5*out['velocity']+out['vf'])
  if previous:
   prior=previous[w]['position'];ev['previous_final']=prior;ev['rebuild_delta']=[x-y for x,y in zip(old,prior)]
  if support:
   key=support['surface'];origin=[64*(key[1+i]+key[4+i]) for i in range(3)];normal=key[7:10]
   ev['support_target']=support['target'];ev['old_depth_relative_target']=sum((x-o)*n for x,o,n in zip(old,origin,normal))-support['target']
   ev['new_depth_relative_target']=sum((x-o)*n for x,o,n in zip(new,origin,normal))-support['target']
  if changed and oldquery['plane']==12 and row['plane']==14:
   boundary=65536*((old[2]>>16)+1)
   assert old[2]<boundary<=new[2]
   alpha=Fraction(boundary-old[2],new[2]-old[2]);ev['translation_seam_fraction']=str(alpha);ev['translation_seam_time']=float(Fraction(t-1,50)+alpha/50)
   if previous:
    prior=previous[w]['position'];beta=Fraction(boundary-prior[2],new[2]-prior[2]);ev['whole_span_seam_fraction']=str(beta);ev['whole_span_seam_time']=float(Fraction(t-1,50)+beta/50)
  events.append(ev)
 previous=record['output']['wheels']
report=dict(events=events,scope='Observed events in recursively simulated acquired-depth candidate with prescribed canonical distance. Translation and whole-span secants are geometric diagnostics, not established event times or new gravity impulses.')
(root/'anchored-release-trace.json').write_text(json.dumps(report,indent=2)+'\n')
for ev in events:
 if 552<=ev['tick']<=568:print(json.dumps(ev))
