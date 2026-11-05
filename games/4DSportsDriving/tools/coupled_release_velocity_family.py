#!/usr/bin/env python3
"""Counterfactual attribution of front/rear release velocities across approach phases.

At11.6s replace only chosen wheel velocity words/fifths by that phase's actual
native20 values; all other50Hz state is preserved. Continue full coupled engine,
terrain, contact and body recurrence. Not a candidate, impulse or release law.
"""
from pathlib import Path
from copy import deepcopy
import json,hashlib
from coupled_vehicle_core import seed,advance,summarize
root=Path('tmp/prof');reports=[]
for phase in ('nominal','minus64','plus64'):
 caps={20:'natural-crest20' if phase=='nominal' else 'phase-'+phase+'-native20',50:'crest-d9e7903' if phase=='nominal' else 'phase-'+phase+'-d9'}
 starts={};readers={};parameters={};native={};checks={}
 for hz,cap in caps.items():
  b,read,param=seed(root/cap);readers[hz]=read;parameters[hz]=param
  reference={v['tick']:v for v in json.loads((root/cap/'bridge.json').read_text())['rows']};checks[str(hz)]=0
  while b['contact']['entry'][0]<=13*hz:
   tick=b['contact']['entry'][0];b,_=advance(b,hz,read,param);v=summarize(b)
   assert v['position']+[v['pitch'],v['speed']]==[reference[tick][k]for k in ('x','y','z','pitch','speed')],(phase,hz,tick)
   checks[str(hz)]+=1
   if tick==58*hz//5:starts[hz]=deepcopy(b)
   if hz==20:native[tick]=v
 starts50=starts[50];entry50=starts50['contact']['entry'];entry20=starts[20]['contact']['entry'];cases={}
 for name,wheels in [('control',()),('front',(0,1)),('rear',(2,3)),('both',(0,1,2,3))]:
  b=deepcopy(starts50);e=b['contact']['entry'];changed=[]
  for w in wheels:
   for off,value in ((21,entry20[21+w]),(25,0)):
    if e[off+w]!=value:changed.append(dict(index=off+w,before=e[off+w],after=value));e[off+w]=value
  assert all(x==y or i in [z['index']for z in changed]for i,(x,y)in enumerate(zip(e,entry50)))
  assert b['car']==starts50['car'] and b['carry']==starts50['carry']
  rows=[];first_contact=None;ledger=dict(body_y4=0,forward_y4=0,gravity_y4=0,rounding_y4=0)
  while b['contact']['entry'][0]<=650:
   tick=b['contact']['entry'][0];old_y=b['contact']['position'][1];b,rec=advance(b,50,readers[50],parameters[50]);v=summarize(b)
   c=rec['contact'];out=c['output'];assert all(w['branch']=='air'for w in out['wheels'])
   assert all(su['returned']==su['extension']==c['entry'][13+w]for w,su in enumerate(out['suspensions']))
   movement=[q['world_y']-q['old_world_y']for q in c['selected']];assert len(set(movement))==1
   dy=4*(v['position'][1]-old_y);forward=4*movement[0];gravity=sum(w['down']for w in out['wheels'])
   ledger['body_y4']+=dy;ledger['forward_y4']+=forward;ledger['gravity_y4']+=gravity;ledger['rounding_y4']+=dy-forward+gravity
   if first_contact is None and any(w['branch']!='air'for w in rec['contact']['output']['wheels']):first_contact=tick
   if name=='control':
    ref={x['tick']:x for x in json.loads((root/caps[50]/'bridge.json').read_text())['rows']}[tick]
    assert v['position']+[v['pitch'],v['speed']]==[ref[k]for k in ('x','y','z','pitch','speed')]
   if tick%10==0:
    n=native[tick*2//5];error=dict(position=[y-x for x,y in zip(n['position'],v['position'])],**{k:v[k]-n[k]for k in ('pitch','speed','target','rpm')})
    rows.append(dict(tick=tick,state=v,error=error))
  assert ledger['body_y4']==ledger['forward_y4']-ledger['gravity_y4']+ledger['rounding_y4']
  cases[name]=dict(changed_fields=changed,first_contact_tick=first_contact,rows=rows,endpoint=rows[-1]['error'],height_ledger_quarters=ledger)
 for name,v in cases.items():
  v['height_change_from_control_quarters']={k:v['height_ledger_quarters'][k]-cases['control']['height_ledger_quarters'][k]for k in ledger}
 reports.append(dict(phase=phase,release_state_native=summarize(starts[20]),release_state50=summarize(starts[50]),exact_baseline_updates=checks,release_velocity_native=entry20[21:25],release_velocity50_fifths=[5*entry50[21+w]+entry50[25+w]for w in range(4)],cases=cases))
# Existing native-velocity live diagnostic is an independent nominal endpoint anchor.
assert reports[0]['cases']['control']['endpoint']['position'][1]==2263
assert reports[0]['cases']['both']['endpoint']['position'][1]==282
assert reports[0]['cases']['both']['endpoint']['pitch']==3
report=dict(scope=__doc__,cases=reports,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(root/'coupled-release-velocity-family.json').write_text(json.dumps(report,indent=2)+'\n')
for row in reports:print(json.dumps(dict(phase=row['phase'],native_velocity=row['release_velocity_native'],a4000_velocity_fifths=row['release_velocity50_fifths'],endpoints={k:dict(error=v['endpoint'],first_contact_tick=v['first_contact_tick'],height_change_quarters=v['height_change_from_control_quarters'])for k,v in row['cases'].items()})))
