#!/usr/bin/env python3
"""Counterfactual: remove newly introduced body-rebuild penetration in BOTH rates.

Not a candidate: native handling itself contains this effect. Retains all other
wheel/suspension/angle laws and applies only the minimal upward body translation
that keeps previously resolved contacts above their SAME selected planes.
"""
import json,hashlib
from pathlib import Path
from copy import deepcopy
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import plane,rotate,sine,word,UnsupportedContact
from native20_contact_model import body as body20
from contact_body_predictor import body as body50
root=Path('tmp/prof');cases=[]
def wrapper(hz,events):
 def solve(e,build,selected,state):
  out=body20(e,build,selected,hz=20)if hz==20 else body50(e,build,selected)
  pitch=out['pitch'];sn,cs=sine(pitch),sine(pitch+256);m=[16384,0,0,0,cs,-sn,0,sn,cs];targets=[]
  for w,(q,end,su)in enumerate(zip(selected,out['wheels'],out['suspensions'])):
   geo={k:q[k]for k in ('plane','normal_x','normal_y','normal_z')};geo.update({'origin_'+a:word(q['base_'+a]+q['node_'+a])for a in 'xyz'})
   if end['branch']=='air' or plane(geo,end['position'])<0:continue
   assert geo['plane']<4 or geo['normal_y']>0,'Upward-only diagnostic domain'
   x,z=((-960,1984),(960,1984),(960,-1984),(-960,-1984))[w]
   rebuilt=[a+d for a,d in zip(out['position'],rotate([x,-384-su['extension'],z],m))]
   targets.append((geo,rebuilt))
  def valid(d):return all(plane(g,[v[0],v[1]+d,v[2]])>=0 for g,v in targets)
  d=0
  if not valid(0):
   hi=1
   while not valid(hi):
    hi*=2
    if hi>65536:raise UnsupportedContact('No supported upward resolution')
   lo=0
   while hi-lo>1:
    mid=(lo+hi)//2
    if valid(mid):hi=mid
    else:lo=mid
   d=hi;assert valid(d)and not valid(d-1)
   out['position'][1]+=d
  events.append(d)
  return out
 return solve
for phase,seed_tick in [('nominal',261),('minus64',259),('plus64',261)]:
 cap=root/('natural-crest20'if phase=='nominal'else 'phase-'+phase+'-native20');initial,read,param=seed(cap)
 ref={r['tick']:r for r in json.loads((root/('coupled-course20-baseline'+(''if phase=='nominal'else '-'+phase)+'.json')).read_text())['rows']}
 while initial['contact']['entry'][0]<=seed_tick:
  t=initial['contact']['entry'][0];initial,_=advance(initial,20,read,param);v=summarize(initial);assert v['position']+[v['pitch'],v['speed']]==[ref[t][k]for k in ('x','y','z','pitch','speed')]
 variants={}
 for label in ('baseline','no_reentry'):
  rates={}
  for hz in (20,50):
   b=deepcopy(initial);events=[];steps=[]
   if hz==50:
    for o in (0xc6,0xcb):b['car'][o]=(5*b['car'][o]+1)//2
   try:
    for i in range(hz//10):
     b,_=advance(b,hz,read,param,solver=wrapper(hz,events)if label=='no_reentry'else None);steps.append(summarize(b))
    rates[str(hz)]=dict(steps=steps,upward_translation=events,final=summarize(b))
   except UnsupportedContact as ex:rates[str(hz)]=dict(unsupported=str(ex),steps=steps,upward_translation=events)
  variants[label]=rates
 result=dict(phase=phase,seed_tick20=seed_tick,variants=variants)
 result['errors50vs20']={}
 for label,rates in variants.items():
  if all('final'in rates[str(h)]for h in (20,50)):
   a,b=[rates[str(h)]['final']for h in (20,50)];result['errors50vs20'][label]=dict(position=[y-x for x,y in zip(a['position'],b['position'])],pitch=b['pitch']-a['pitch'],speed=b['speed']-a['speed'])
 cases.append(result)
report=dict(scope=__doc__,duration_ms=100,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases)
(root/'contact-reprojection-ablation.json').write_text(json.dumps(report,indent=2)+'\n')
for c in cases:print(c['phase'],c['errors50vs20'],{h:r.get('upward_translation')for h,r in c['variants']['no_reentry'].items()})
