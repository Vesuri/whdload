#!/usr/bin/env python3
"""Validate native20 wheel, suspension and straight body reconstruction."""
import json,collections
from pathlib import Path
from native20_contact_model import wheel,suspension
from native_contact_response import rotate,atan_native
from airborne_pitch_predictor import axis
p=Path('tmp/prof/native20-contact-model');data=json.loads((p/'prediction.json').read_text());r=data['records']
entries={e[0]:e for e in r['ENTRY']};final={(x[0],x[1]):x[2:] for x in r['FINAL']};sinputs={(x[0],x[1]):x[2:] for x in r['SUSP_IN']};soutputs={(x[0],x[1]):x[2:] for x in r['SUSP_OUT']};bodies={x[0]:x[1:] for x in r['BODY']}
branches=collections.Counter();sbranches=collections.Counter();wheels={};lifts={};failures=[];positions=0;pitches=0
for row in r['SELECT']:
 t,w=row['tick'],row['wheel'];e=entries[t]
 assert row['velocity_fraction']==row['position_fraction']==row['extension_fraction']==0
 out=wheel(row);expected=out['position']+[out[k] for k in ('clearance','velocity','vf','pf','ef')]
 assert final[t,w]==expected,(t,w,'wheel',final[t,w],expected)
 sin=sinputs[t,w];assert sin==[out['suspension_clearance'],e[13+w],e[17+w],out['ef'],e[37+w]],(t,w,sin)
 su=suspension(e[13+w],e[17+w],out['suspension_clearance'],0,0)
 assert soutputs[t,w]==[su[k] for k in ('returned','extension','bias','ef','bf')],(t,w,'susp',soutputs[t,w],su)
 branches[out['branch']]+=1;sbranches[(su['branch_clearance']>0)-(su['branch_clearance']<0)]+=1
 wheels[t,w]=out;lifts[t,w]=su['returned']
for t,e in entries.items():
 assert e[1]==e[3]==0
 basis=[[x+y for x,y in zip(wheels[t,w]['position'],rotate([0,384+lifts[t,w],0],e[4:13]))] for w in range(4)]
 pos=[sum(v[i] for v in basis)//4 for i in range(3)]
 if pos==bodies[t][:3]:positions+=1
 else:failures.append(dict(tick=t,kind='position',predicted=pos,actual=bodies[t][:3]))
 pitch=atan_native(*axis(basis))-256
 if abs(pitch)<2:pitch=0
 if pitch==bodies[t][4]:pitches+=1
 else:failures.append(dict(tick=t,kind='pitch',predicted=pitch,actual=bodies[t][4]))
report=dict(wheels=len(wheels),suspensions=len(wheels),positions=positions,pitches=pitches,fullstates=data['matching_full_states'],branches=dict(branches),suspension_branches=dict(sbranches),failures=failures,
 scope='Read-only native20Hz straight course; selected terrain and dynamic inputs supplied. No general heading/roll, nonzero suspension bias, hard crash, arbitrary terrain or same-state cross-rate trajectory proof yet.')
(p/'model-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert not failures
