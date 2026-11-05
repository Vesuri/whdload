#!/usr/bin/env python3
"""Reconstruct tilt geometry for recorded matched second-transition responses."""
import json
from pathlib import Path
from native_contact_response import rotate,atan_native
from airborne_pitch_predictor import axis,atan_q8,wrap
from contact_body_predictor import tilt
p=Path('tmp/prof');source=json.loads((p/'coupled-second-transition-probe.json').read_text());rows=[]
for case in source['cases']:
 for r in case['paths']['50']:
  e=r['entry'];m=e[4:13];old=[];final=[]
  for w in range(4):
   old.append([a+b for a,b in zip(e[45+3*w:48+3*w],rotate([0,384+e[13+w],0],m))])
   final.append([a+b for a,b in zip(r['output']['wheels'][w]['position'],rotate([0,384+r['output']['suspensions'][w]['returned'],0],m))])
  result=tilt(old,final,e[41]);assert result==(r['output']['pitch'],r['output']['pitch_carry'])
  initial=atan_native(*axis(old))-256;native=atan_native(*axis(final))-256
  if abs(native)<2:native=0
  delta=wrap(atan_q8(*axis(final))-atan_q8(*axis(old)),18)
  rows.append(dict(phase=case['phase'],ms=r['ms'],initial=e[2],baseline=initial,carry=e[41],geometry_delta_q8=delta,current_pitch=result[0],current_carry=result[1],native_at_same_endpoint=native,pitch_difference=result[0]-native))
report=dict(scope=__doc__,checked=len(rows),baseline_mismatches=[r for r in rows if r['initial']!=r['baseline']],maximum_same_endpoint_pitch_difference=max(abs(r['pitch_difference'])for r in rows),rows=rows)
(p/'second-transition-tilt-audit.json').write_text(json.dumps(report,indent=2)+'\n');print({k:v for k,v in report.items()if k!='rows'})
for r in rows:
 if r['initial']!=r['current_pitch'] and r['ms']<=14100:print(r)
