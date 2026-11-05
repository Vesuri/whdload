#!/usr/bin/env python3
"""Paired same-input classification comparison on exact baseline trajectories."""
from pathlib import Path
from unittest.mock import patch
from collections import Counter
import json
import contact_body_predictor as model
from coupled_vehicle_core import seed,advance,summarize
from native_contact_response import resolve,UnsupportedContact
r=Path('tmp/prof');cases=[]
for phase in ('nominal','minus64','plus64'):
 b,read,param=seed(r/('crest-d9e7903'if phase=='nominal'else'phase-'+phase+'-d9'));suffix=''if phase=='nominal'else'-'+phase
 baseline=json.loads((r/('coupled-course-baseline'+suffix+'.json')).read_text())['rows'];tick=[0];changes=[];counts=Counter()
 def compare(*args):
  original=resolve(*args);counts[original['branch']]+=1
  try:other=resolve(*args,coherent_clearance=True)
  except UnsupportedContact as exc:changes.append(dict(tick=tick[0],original_branch=original['branch'],unsupported=str(exc)));return original
  if other['branch']!=original['branch']or other['position']!=original['position']:
   changes.append(dict(tick=tick[0],original_branch=original['branch'],candidate_branch=other['branch'],endpoint_delta=[v-u for u,v in zip(original['position'],other['position'])]))
  return original
 with patch.object(model,'resolve',compare):
  for expected in baseline:
   tick[0]=b['contact']['entry'][0];b,_=advance(b,50,read,param);s=summarize(b)
   assert s['position']+[s['pitch'],s['speed']]==[expected[k]for k in ('x','y','z','pitch','speed')]
 cases.append(dict(phase=phase,exact_steps=len(baseline),original_branches=dict(counts),changes=changes))
(r/'normal-clearance-same-input-audit.json').write_text(json.dumps(dict(scope=__doc__,cases=cases),indent=2)+'\n')
for c in cases:print(c['phase'],'changed_calls',len(c['changes']),'first',c['changes'][:2], 'pairs',Counter((v['original_branch'],v.get('candidate_branch','unsupported'))for v in c['changes']))
