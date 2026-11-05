#!/usr/bin/env python3
"""Port only the independently derived distance experiment to current source."""
from pathlib import Path
import shutil,json,hashlib
old=Path('tmp/fixtures/distance-order/source');dst=Path('tmp/fixtures/ordered-distance-d9/source');current=Path('src');assert not dst.exists();shutil.copytree(current,dst)
for filename,start,end in [('simulation_a4000.s','sim_a4000_distance:','; $F60C'),('simulation_a4000.s','sim_a4000_acceleration:','; JMP hook at $1033A'),('simulation_physics.s','sim_distance_50:','; Approach target')]:
 p=dst/filename;s=p.read_text();o=(old/filename).read_text();a=s.index(start);b=s.index(end,a);oa=o.index(start);ob=o.index(end,oa);p.write_text(s[:a]+o[oa:ob]+s[b:])
p=dst/'4DSportsDrivingHD.s';s=p.read_text();needle='    PL_PSS $F60C,sim_a4000_acceleration,10';assert s.count(needle)==1;s=s.replace(needle,needle+'\n    PL_PSS $F66E,sim_distance_order_prepare,2');p.write_text(s)
changed=[p.name for p in dst.iterdir() if p.is_file() and p.read_bytes()!=(current/p.name).read_bytes()];assert sorted(changed)==['4DSportsDrivingHD.s','simulation_a4000.s','simulation_physics.s']
(dst.parent/'manifest.json').write_text(json.dumps({'base':'d9e7903','changed_files':changed,'scope':'Distance carry denominator400 and continuous engine delta eligibility only. Experimental private32..39 use; no replay compatibility or release claim. Current tilt/display fixes retained.'},indent=2)+'\n')
for name in ('control','intervention'):
 s=Path(f'tools/contact_approach_{name}.py').read_text().replace('crest-d9e7903/bridge.json','ordered-distance-d9-crest/bridge.json').replace("tmp/prof/crest-d9e7903','bridge-end.bin'","tmp/prof/ordered-distance-d9-crest','bridge-end.bin'")
 Path(f'tools/contact_ordered_{name}.py').write_text(s)
