#!/usr/bin/env python3
"""Read-only sensitivity of native queries to pending extension fifths.
Reconstruct the captured baseline exactly, then independently query each wheel
with its pending extension fraction included before the integer Q14 projection.
Alternative queries do not feed back into the baseline trajectory.
"""
import json
from pathlib import Path
from coupled_vehicle_core import seed,advance,summarize
from crest_terrain_query import query
from supported_plane_model import geometry
from native_contact_response import rotate,word
r=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=r/('crest-d9e7903'if phase=='nominal'else'phase-'+phase+'-d9');b,read,param=seed(cap);ref={v['tick']:v for v in json.loads((cap/'bridge.json').read_text())['rows']};changes=[];nonzero=0;wheels=0;steps=0
 while b['contact']['entry'][0]<=800:
  position=b['contact']['position'].copy();cached=[x.copy()for x in b['contact']['cached']];b,rec=advance(b,50,read,param);c=rec['contact'];e=c['entry'];m=e[4:13];t=e[0];v=summarize(b)
  assert v['position']+[v['pitch'],v['speed']]==[ref[t][k]for k in ('x','y','z','pitch','speed')];steps+=1
  delta=rotate([0,0,rec['engine']['distance']],m)
  for w,local in enumerate(c['build']):
   f=e[33+w];assert 0<=f<5;wheels+=1;nonzero+=bool(f)
   base=c['selected'][w];baseline=[base['world_'+a]for a in 'xyz']
   projected=[word((5*sum(local[j]*m[3*j+i]for j in range(3))-f*m[3+i])//(5*16384))for i in range(3)]
   alternative=[x+y+z for x,y,z in zip(position,projected,delta)];diff=[x-y for x,y in zip(alternative,baseline)];assert max(map(abs,diff))<=1
   alt=query(alternative,cached[w]);oldq,newq=base['clearance'],alt['clearance']
   if geometry(alt)!=geometry(base) or oldq!=newq:
    changes.append(dict(tick=t,wheel=w,extension=e[13+w],fraction=f,position_delta=diff,old_plane=base['plane'],new_plane=alt['plane'],old_clearance=oldq,new_clearance=newq,gravity_decision_changed=(oldq>0)!=(newq>0),penetration_decision_changed=(oldq<0)!=(newq<0)))
 report=dict(phase=phase,exact_steps=steps,wheels=wheels,nonzero_extension_fractions=nonzero,query_changes=changes,gravity_decision_changes=sum(x['gravity_decision_changed']for x in changes),penetration_decision_changes=sum(x['penetration_decision_changed']for x in changes));cases.append(report)
 print(phase,'steps',steps,'fractions',nonzero,'query changes',len(changes),'gravity',report['gravity_decision_changes'],'penetration',report['penetration_decision_changes']);print([x for x in changes if x['gravity_decision_changed']or x['penetration_decision_changed']][:8])
(r/'extension-fraction-geometry-audit.json').write_text(json.dumps(dict(scope=__doc__,cases=cases),indent=2)+'\n')
