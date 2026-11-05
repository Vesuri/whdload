#!/usr/bin/env python3
"""Fixed-path accounting for splitting gravity only at the observed seam."""
import json
from fractions import Fraction
from pathlib import Path
root=Path('tmp/prof');trace=json.loads((root/'anchored-release-trace.json').read_text());run=json.loads((root/'anchored-support-probe.json').read_text())
end=next(r for r in run['records'] if r['tick']==580);rows=[]
for event in trace['events']:
 if 'translation_seam_fraction' not in event or not 550<=event['tick']<=570:continue
 w=event['wheel'];a=21 if w<2 else 15;alpha=Fraction(event['translation_seam_fraction'])
 v=Fraction(5*end['wheels'][w]['velocity']+end['wheels'][w]['vf'],5)
 removed=Fraction(2*a,5)*alpha;native=189 if w<2 else 105
 rows.append(dict(wheel=w,seam_time=event['translation_seam_time'],rebuild_delta=event['rebuild_delta'],
  gravity_removed=str(removed),current_velocity=str(v),seam_only_velocity=str(v-removed),
  native20_velocity=native,current_gap=str(native-v),seam_only_gap=str(native-v+removed)))
assert len(rows)==4 and all(Fraction(r['seam_only_gap'])>Fraction(r['current_gap']) for r in rows)
report=dict(rows=rows,scope='Exact force-duration accounting on the FIXED acquired-depth trajectory through11.6s. A new simulation can feed back and change geometry/timing; this is not its predicted final path. Shows that simply removing pre-seam gravity does not repair this fixed-path velocity gap.')
(root/'anchored-release-accounting.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
