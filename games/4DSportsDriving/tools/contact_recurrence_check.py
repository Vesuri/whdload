#!/usr/bin/env python3
"""Recursively reproduce contact state with externally supplied forward distances.

This excludes drivetrain evolution. No later position/orientation/contact state
is injected after the initial step; observed distance/roof/impact are supplied.
"""
import json,struct
from pathlib import Path
from native_contact_response import rotate,sine
from contact_body_predictor import body as body50
from native20_contact_model import body as body20
from crest_terrain_query import query
from contact_step import step
root=Path('tmp/prof');results=[]
for hz,capture,baseline in ((50,'contact-prediction-d9','crest-d9e7903'),(20,'native20-contact-model','natural-crest20')):
 cap=root/capture;r=json.loads((cap/'prediction.json').read_text())['records'];meta=json.loads((cap/'anchor.json').read_text());memory=(cap/'memory.bin').read_bytes()
 car=meta['data_base']+0x7ffe-0x92e-meta['memory_base'];cached=[list(struct.unpack_from('>3h',memory,car+0x74+6*w)) for w in range(4)]
 canonical={x['tick']:x for x in json.loads((root/baseline/'bridge.json').read_text())['rows']}
 selected={(x['tick'],x['wheel']):x for x in r['SELECT']};actualbody={x[0]:x[1:] for x in r['BODY']}
 prev=canonical[r['ENTRY'][0][0]-1];position=[prev[k] for k in ('x','y','z')];e=r['ENTRY'][0].copy();completed=0
 state=dict(entry=e,position=position,cached=cached)
 for observed in r['ENTRY']:
  t=observed[0]
  state,record=step(state,hz,selected[t,0]['distance'],[selected[t,w]['correction'] for w in range(4)],[selected[t,w]['impact_flags'] for w in range(4)])
  assert record['entry']==observed,(hz,t)
  out=record['output'];actual=actualbody[t]
  assert out['position']+[0,out['pitch'],0,out['pitch_carry']]+out['centroid_carries']==actual,(hz,t)
  completed+=1
 position=state['position']
 results.append(dict(rate=hz,steps=completed,exact_entry_words=completed*69,final_position=position))
report=dict(results=results,scope='Contact subsystem recurrence from initial pose/state/cached wheels; all later pose, wheel state, carries and geometry are predicted. Observed forward distance, roof/impact inputs supplied; drivetrain/controller are not simulated. Original straight course only.')
(root/'contact-recurrence-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
