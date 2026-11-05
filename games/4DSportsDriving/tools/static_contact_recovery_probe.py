#!/usr/bin/env python3
"""Equal-pose contact recovery with zero or equal prescribed forward distance.

This is a subsystem diagnostic, not a braking maneuver or accepted physics.
Native20 seeds are reproduced exactly; no fitted impulses or changed limits.
"""
import json,hashlib
from copy import deepcopy
from pathlib import Path
from coupled_vehicle_core import seed,advance,summarize
from contact_step import step
from native_contact_response import UnsupportedContact
root=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 cap=root/('natural-crest20' if phase=='nominal' else 'phase-'+phase+'-native20')
 b,read,param=seed(cap);refs={r['tick']:r for r in json.loads((cap/'bridge.json').read_text())['rows']};checked=0;rows=[]
 while b['contact']['entry'][0]<=270:
  t=b['contact']['entry'][0];b,_=advance(b,20,read,param);v=summarize(b)
  assert v['position']+[v['pitch'],v['speed']]==[refs[t][k]for k in ('x','y','z','pitch','speed')],(phase,t)
  checked+=1
  if t<190:continue
  _,next_record=advance(deepcopy(b),20,read,param)
  distance=next_record['engine']['distance'];variants={}
  for moving in (False,True):
   rates={}
   for hz in (10,20,50):
    state=deepcopy(b['contact']);state['entry'][0]=1;history=[]
    try:
     for k in range(hz//10):
      issued=((k+1)*2*distance//(hz//10)-k*2*distance//(hz//10)) if moving else 0
      state,r=step(state,hz,issued);o=r['output']
      history.append(dict(distance=issued,position=state['position'],pitch=state['entry'][2],pitch_carry=state['entry'][41],branches=[w['branch']for w in o['wheels']],planes=[q['plane']for q in r['selected']],clearance=[q['clearance']for q in r['selected']],gravity=[w['down']for w in o['wheels']],extensions=state['entry'][13:17],returns=[s['returned']for s in o['suspensions']]))
     rates[str(hz)]=dict(final=history[-1],steps=history)
    except UnsupportedContact as e:rates[str(hz)]=dict(unsupported=str(e),steps=history)
   variants['moving' if moving else 'zero']=rates
  rates=variants['zero']
  row=dict(seed_tick20=t,seed_time_ms=t*50,initial=v,rates=rates,moving_rates=variants['moving'],prescribed_distance20=distance)
  if all('final'in rates[str(h)]for h in (20,50)):
   q=rates['20']['final']
   for label,h in [('error50',50),('error10',10)]:
    if 'final'in rates[str(h)]:row[label]=dict(pitch=rates[str(h)]['final']['pitch']-q['pitch'],position=[v-u for u,v in zip(q['position'],rates[str(h)]['final']['position'])])
  rates=variants['moving']
  if all('final'in rates[str(h)]for h in (10,20,50)):
   q=rates['20']['final'];row['moving_error50']=dict(pitch=rates['50']['final']['pitch']-q['pitch'],position=[v-u for u,v in zip(q['position'],rates['50']['final']['position'])])
   for hz in (10,20,50):assert sum(v['distance']for v in rates[str(hz)]['steps'])==2*distance
  rows.append(row)
 good=[r for r in rows if 'error50'in r];summary={}
 for k,idx in [('y',1),('z',2),('pitch',None)]:
  value=lambda r:abs(r['error50']['pitch']if idx is None else r['error50']['position'][idx])
  worst=max(good,key=value);summary[k]=dict(maximum=value(worst),seed_tick20=worst['seed_tick20'],error50=worst['error50'],error10=worst.get('error10'))
 moving_good=[r for r in rows if 'moving_error50'in r]
 moving_summary={}
 for k,idx in [('y',1),('z',2),('pitch',None)]:
  value=lambda r:abs(r['moving_error50']['pitch']if idx is None else r['moving_error50']['position'][idx])
  worst=max(moving_good,key=value);moving_summary[k]=dict(maximum=value(worst),seed_tick20=worst['seed_tick20'],moving_error50=worst['moving_error50'],zero_error50=worst.get('error50'))
 cases.append(dict(moving_summary=moving_summary,moving_supported=len(moving_good),phase=phase,exact_native_steps=checked,supported=len(good),total=len(rows),summary=summary,rows=rows))
report=dict(scope=__doc__,duration_ms=100,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cases=cases)
(root/'static-contact-recovery-probe.json').write_text(json.dumps(report,indent=2)+'\n')
for c in cases:print(c['phase'],c['supported'],c['summary'],'moving',c['moving_summary'])
