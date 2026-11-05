#!/usr/bin/env python3
"""Quantify p=2 vs p=5 handling from a completed frozen-build car matrix."""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('matrix',type=Path);a=p.parse_args()
m=json.loads(a.matrix.read_text());assert m['status']=='PASS','matrix incomplete'
rows={};report=[]
for row in m['captures']:rows[row['car'],row['period'],row['tape']]=row
assert set(rows)=={(c,p,t) for c in range(5) for p in [2,5] for t in ['straight','route']},'full five-car matrix required'
for car in range(5):
 for tape in ['straight','route']:
  aa=[]
  for period in [2,5]:
   row=rows[car,period,tape];d=a.matrix.parent/row['name']
   cm=json.loads((d/'capture.json').read_text());assert cm['slave_sha256']==m['slave_sha256']
   s=json.loads((d/'states/samples.json').read_text())
   aa.append({x['vbl']-x['epoch']:x for x in s})
  fine,coarse=aa;assert fine.keys()==coarse.keys()
  fields=sorted(fine);end=fields[-1];origin=fields[0]
  travel=coarse[end]['pos']-coarse[origin]['pos'];diff=fine[end]['pos']-coarse[end]['pos']
  r=dict(car=car,tape=tape,fields=len(fields),peak_mph=[max(x['speed'] for x in arm.values())/65536 for arm in aa],travel_difference_units=diff/65536,travel_difference_percent=100*diff/travel if travel else None,max_speed_difference_mph=max(abs(fine[i]['speed']-coarse[i]['speed']) for i in fields)/65536,end_lateral_difference_units=(fine[end]['x']-coarse[end]['x'])/65536,max_lateral_difference_units=max(abs(fine[i]['x']-coarse[i]['x']) for i in fields)/65536)
  report.append(r)
print(json.dumps(dict(status='MEASURED',slave_sha256=m['slave_sha256'],order='p2, p5',scope='Scripted straight and steering inputs; differences are measurements, not an arbitrary tolerance-based fidelity verdict',cars=report),indent=2))
