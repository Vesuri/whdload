#!/usr/bin/env python3
"""Exact phase-average endpoint force bias; not a contact-law proof."""
import json
from fractions import Fraction as F
from pathlib import Path
ends20=[F(i,20) for i in (1,2)];ends50=[F(i,50) for i in range(1,6)]
edges=sorted(set([F(0)]+ends20+ends50));reports=[]
for a in (21,15):
 rows=[];mean=F(0);square=F(0);corrected_square=F(0);correction=F(3*a,10)
 for lo,hi in zip(edges,edges[1:]):
  phase=(lo+hi)/2;weight=(hi-lo)/F(1,10)
  v20=a*sum(t>phase for t in ends20);v50=F(2*a,5)*sum(t>phase for t in ends50);error=v50-v20
  mean+=weight*error;square+=weight*error**2;corrected_square+=weight*(error+correction)**2
  rows.append(dict(start=str(lo),end=str(hi),v20=str(v20),v50=str(v50),error=str(error),corrected_error=str(error+correction)))
 assert mean==-correction
 reports.append(dict(acceleration_per_native_step=a,mean_error=str(mean),time_derived_correction=str(correction),mean_square=str(square),corrected_mean_square=str(corrected_square),rows=rows))
report=dict(rates=reports,scope='One prescribed airborne activation uniformly phased within100ms, constant acceleration, no contact feedback/resets. Difference in endpoint quadrature mean equals a*(1-.4)/2. Does not prove the same correction valid for deterministic geometry, impact or repeated contact.')
p=Path('tmp/prof/endpoint-force-bias.json');p.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
