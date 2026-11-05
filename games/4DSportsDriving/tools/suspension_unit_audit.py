#!/usr/bin/env python3
"""Demonstrate terrain-clearance versus wheel-extension coordinate units."""
import json
from pathlib import Path
from native_contact_response import plane,rotate
from native20_contact_model import suspension as native
from contact_body_predictor import suspension as current
from extension_rate_cap_model import suspension as candidate
geo=dict(plane=0,origin_x=0,origin_y=0,origin_z=0,normal_x=0,normal_y=8192,normal_z=0);m=[16384,0,0,0,16384,0,0,0,16384];rows=[]
for clearance in (1,10,64,100,192,256):
 world=[0,clearance*64,0];assert plane(geo,world)==clearance
 outcomes={}
 for name,fn in [('native20',native),('current50',current),('rejected_cap50',candidate)]:
  out=fn(0,0,clearance,0,0);movement=rotate([0,-out['extension'],0],m)
  assert movement==[0,-out['extension'],0]
  nextpoint=[a+b for a,b in zip(world,movement)]
  outcomes[name]=dict(extension_raw=out['extension'],fraction=out['ef'],remaining_gap_raw=nextpoint[1],remaining_clearance=plane(geo,nextpoint),returned_offset=out['returned'])
  assert out['returned']==0
 rows.append(dict(clearance_coarse=clearance,gap_raw=clearance*64,outcomes=outcomes))
report=dict(scope=__doc__,clearance_unit_raw=64,extension_unit_raw=1,native_unsaturated_gain='1/64 per native update',current50_unsaturated_gain='(2/5)/64 per update, plus exact fifth carry',qualification='Flat identity geometry and zero initial extension/bias; returned offset is old extension, so movement shown is next wheel-build effect, not a same-step body impulse.',rows=rows)
Path('tmp/prof/suspension-unit-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
