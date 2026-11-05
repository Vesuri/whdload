#!/usr/bin/env python3
"""Classify contact events causally; this defines no replacement response."""
import json,struct,collections
from fractions import Fraction
from pathlib import Path
from native_contact_response import UnsupportedContact,resolve,word
from native20_contact_model import wheel as wheel20
from contact_body_predictor import wheel as wheel50
from crest_terrain_query import query
root=Path('tmp/prof');reports=[]
for hz,name in ((20,'native20-contact-model'),(50,'contact-prediction-d9')):
 cap=root/name;r=json.loads((cap/'prediction.json').read_text())['records'];meta=json.loads((cap/'anchor.json').read_text());mem=(cap/'memory.bin').read_bytes();car=meta['data_base']+0x7ffe-0x92e-meta['memory_base']
 final={(v[0],v[1]):v[2:5] for v in r['FINAL']};start=r['ENTRY'][0][0];events=[]
 for row in r['SELECT']:
  t,w=row['tick'],row['wheel'];out=(wheel20 if hz==20 else wheel50)(row)
  if out['branch'] in ('zero','air'):continue
  cached=list(struct.unpack_from('>3h',mem,car+0x74+6*w)) if t==start else [v>>6 for v in final[t-1,w]]
  old=[row['old_world_'+a] for a in 'xyz'];new=[row['world_'+a] for a in 'xyz'];origin=[row['base_'+a]+row['node_'+a] for a in 'xyz'];normal=[row['normal_'+a] for a in 'xyz']
  def raw(v):return sum((Fraction(x,64)-o)*n for x,o,n in zip(v,origin,normal))/8192
  before,after=raw(old),raw(new)
  try:
   oldquery=query(old,cached);same=all(oldquery[k]==row[k] for k in ('plane','base_x','base_y','base_z'))
  except (UnsupportedContact,ValueError):same=False
  stationary=row['velocity']==0 and row['velocity_fraction']==0
  # Diagnostic label only: an inherited sub-unit depth on the same surface,
  # with no pre-existing gravitational velocity, is not a fresh plane crossing.
  inherited=same and stationary and -1<before<0 and -1<after<0
  detail={}
  if inherited:
   geo=dict(row);geo.update({'origin_'+a:word(row['base_'+a]+row['node_'+a]) for a in 'xyz'})
   response=resolve(old,new,geo,row['distance'],0,0,row['impact_flags'])
   detail={k:response[k] for k in ('before_push','push','stored_clearance','backoff') if k in response}
  events.append(dict(response=detail,tick=t,wheel=w,time=t/hz,branch=out['branch'],same_surface=same,initial_velocity=row['velocity'],
   raw_before=str(before),raw_after=str(after),inherited_subunit_depth=inherited,
   response_delta=[out['position'][i]-new[i] for i in range(3)],plane=row['plane']))
 reports.append(dict(rate=hz,events=events,counts=dict(collections.Counter(x['branch'] for x in events)),
  inherited_subunit_events=sum(x['inherited_subunit_depth'] for x in events),
  inherited_ticks=sorted({x['tick'] for x in events if x['inherited_subunit_depth']})))
report=dict(rates=reports,scope='Causal event labels on unmodified trajectories; same surface plus zero gravity plus inherited raw depth(-1,0) does NOT authorize deleting contact response. Includes no state mutation or candidate integration law.')
(root/'contact-event-inventory.json').write_text(json.dumps(report,indent=2)+'\n')
for r in reports:print({k:v for k,v in r.items() if k!='events'})
