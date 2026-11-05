#!/usr/bin/env python3
"""Summarize changed-motion predictor evidence, preserving scope limits."""
import json,hashlib
from pathlib import Path
from simulation_fixture import read_fixture
root=Path('tmp/prof');base=json.loads((root/'contact-prediction-d9/prediction.json').read_text())['records'];results=[]
for name in ('terrain-motion-identity','terrain-motion-plus64','terrain-motion-minus64'):
 p=root/name;d=json.loads((p/'prediction.json').read_text());r=d['records'];check=json.loads((p/'terrain-body-check.json').read_text())
 anchor=read_fixture(p,'memory.bin');reference=read_fixture(root/'contact-prediction-d9','memory.bin');assert anchor==reference
 assert len(r['ENTRY'])==len(base['ENTRY'])==230
 changes={key:sum(a[key]!=b[key] for a,b in zip(r['SELECT'],base['SELECT'])) for key in ('plane','base_z','clearance','plane_flags')}
 changed_bodies=sum(a!=b for a,b in zip(r['BODY'],base['BODY']))
 if d['shift']==0:
  assert not changed_bodies and not any(changes.values())
  assert d['matching_full_states']==64
 else:assert changed_bodies>0 and changes['plane']>0
 results.append(dict(name=name,shift=d['shift'],verified_writes=d['verified_writes'],initial_fixture_exact=True,
  matching_full_states=d['matching_full_states'],changed_queries=changes,changed_bodies=changed_bodies,
  predicted_bodies=check['body_updates'],predicted_wheels=check['wheels'],predicted_suspensions=check['suspensions'],
  branches=check['branches'],trace_sha256=hashlib.sha256((p/'prediction.json').read_bytes()).hexdigest()))
report=dict(runs=results,scope='Validation of query/contact/body predictor under deliberate common translated-Z changes. Static terrain geometry comes from earlier canonical capture. No new physical integration law, handling acceptance, arbitrary-track/general-rotation or replay/capacity proof.')
(root/'terrain-motion-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
