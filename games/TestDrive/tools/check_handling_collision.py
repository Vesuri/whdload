#!/usr/bin/env python3
import json,re,struct
from pathlib import Path
from harness import ROOT,sha
from audit_simulation import ranges,originals,validate
from check_units import check as units
from check_disabled import check
from timing_map import decode
p=ROOT/'tmp/handling-collision';v=json.loads((p/'units/vectors.json').read_text());q=p/'units-040';m=json.loads((q/'capture.json').read_text());ram=(q/'end/code.bin').read_bytes()
s={n:int(a,16) for n,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(q/'slave.lst').read_text(encoding='latin1'),re.M)};h=m['regions']['td']+0x6390-m['base'];base=int.from_bytes(ram[h+2:h+6],'big')-s['overlay_unload_end']-m['base'];assert struct.unpack_from('>III',ram,base+s['render_verify_results'])==(0,1421,0)
u=units(ram[base:base+s['verify_unit_results']+12],v['expected_count'])
rs=ranges();incoming=validate(rs,originals());smokes={n:check(p/n) for n in ['normal-040-on','normal-040-off']}
for n in smokes:assert sha(p/n/'slave.slave')==sha(ROOT/'tmp/dist/2.0b/TestDrive.slave')
selected=['pos','speed','rpm','gear','step_displacement','steer','x','event','chances','traffic_pos','traffic_speed','traffic_x','oncoming_pos','oncoming_x']
for i in [0,1]:
 a=decode((p/'near-car-before'/f'data-{i:03}.bin').read_bytes());b=decode((p/'near-car-after'/f'data-{i:03}.bin').read_bytes());assert {k:a[k] for k in selected}=={k:b[k] for k in selected}
cartraces={}
for n in ['near-car-before-trace','near-car-after','near-car-after-off']:
 r=[list(map(int,x)) for x in re.findall(r'CAR (-?\d+) (-?\d+) (-?\d+) (-?\d+) (-?\d+)',(p/n/'steps.txt').read_text())];near=[x for x in r if 3<=x[1]<=6];assert near,n
 if n=='near-car-before-trace':assert any(abs(x[2])>10000 for x in near)
 else:assert all(-320<=x[2]<=640 for x in near)
 cartraces[n]=near
route={n:json.loads((p/n/'states.json').read_text())[-1]['position'] for n in ['current-no-steering','original-no-steering','curve-candidate-no-steering']}
assert abs(route['curve-candidate-no-steering']-route['original-no-steering'])<2
assert abs(route['current-no-steering']-route['original-no-steering'])>300
r=dict(status='PASS',slave_sha256=sha(ROOT/'tmp/dist/2.0b/TestDrive.slave'),declared_ranges=len(rs),incoming=incoming,simulation_assertions=u,added_assertions=v['assertions'],renderer_assertions=1421,smokes=smokes,near_car_traces=cartraces,unchanged_collision_fields=selected,first_wall_course_positions=route,limits='Finite native route comparison, not exact period-2/5 identity. Controlled parked-car fixture uses guest code; native debugger input and read-only captures. Real hardware deferred; NTSC unvalidated.',source={f.name:sha(f) for f in (ROOT/'src').iterdir() if f.is_file()})
(p/'acceptance.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['status','slave_sha256','declared_ranges','added_assertions','renderer_assertions','first_wall_course_positions']},indent=2))
