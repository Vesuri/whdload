#!/usr/bin/env python3
"""Exact ordered-pair fractional flow and measured plane-crossing candidates."""
from fractions import Fraction as F
from pathlib import Path
import json,random
p=Path('tmp/prof')
def advance(v,a,h):return v+a*h, h*v+a*h*(h+1)/2
rng=random.Random(4000);count=0
for _ in range(2000):
 v=F(rng.randrange(-300,301),5);a=rng.choice((15,21));h=F(rng.randrange(101),250);k=F(rng.randrange(101),250)
 w,x=advance(v,a,h);u,y=advance(w,a,k);z,t=advance(v,a,h+k);assert (u,x+y)==(z,t);count+=1
for a in (15,21):
 v=F(0);x=F(0)
 for _ in range(5):v,d=advance(v,a,F(2,5));x+=d
 w,y=advance(F(0),a,F(2));assert (v,x)==(w,y)
result=dict(composition_identities=count,full50_pair_identity=True,captures={})
def plane_distance(r,prefix):
 if r['plane']<4:return (r[prefix+'y']-64*(r['base_y']+r['node_y']))*8192
 return sum((r[prefix+a]-64*(r['base_'+a]+r['node_'+a]))*r['normal_'+a] for a in 'xyz')
for name in ('release-step50','release-second-step50'):
 data=json.loads((p/name/'takeoff-plane.json').read_text());events=[]
 gravity={(r['tick'],r['wheel']) for r in data['rows'] if r['event']=='GRAVITY'}
 for r in data['rows']:
  if r['event']!='SELECT' or (r['tick'],r['wheel']) not in gravity or r['velocity'] or r['velocity_fraction']:continue
  old,new=plane_distance(r,'old_world_'),plane_distance(r,'world_');crossing=old<=0<new
  event=dict(tick=r['tick'],wheel=r['wheel'],plane=r['plane'],old_signed_world_distance=float(F(old,8192)),new_signed_world_distance=float(F(new,8192)),geometric_crossing=crossing)
  if crossing:
   duration=F(2,5)*F(new,new-old);v,d=advance(F(0),21 if r['wheel']<2 else 15,duration)
   event.update(duration_nominal20=str(duration),airborne_ms=float(50*duration),velocity=str(v),downward_displacement=str(d))
  else:event['decision']='No plane crossing in the actual segment. Fractional duration cannot be inferred by clamping this ratio; classify supported/contact-quantization state first.'
  events.append(event)
 result['captures'][name]=events
result['scope']='Exact real-arithmetic model and read-only measured geometry; not a runtime patch. F_h(v)=(v+a*h, h*v+a*h*(h+1)/2) preserves the native ordered-pair generator and composes without a timing grid. Current-plane segment crossing is only a candidate release time; pre-existing positive contact gaps, topology, retry ownership, finite precision, native preservation, replay and closed-loop handling remain unvalidated. No mean-phase velocity impulse is introduced.'
(p/'fractional-release-model.json').write_text(json.dumps(result,indent=2)+'\n')
print('composition identities',count)
for name,events in result['captures'].items():
 print(name)
 for e in events:
  if e['wheel'] in (0,2):print(e)
