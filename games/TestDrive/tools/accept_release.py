#!/usr/bin/env python3
"""Validate phase11 release evidence and pin its exact build, reports and captures."""
import hashlib,json,re
from pathlib import Path
from harness import ROOT,sha
from check_disabled import check as byte_check
from check_timing import check as timing_check
from check_units import check as units_check
from check_police import check as police_check
from compare_simulation_demo import compare
from check_simulation_budget import check as budget_check
from subunit_cost import measure as render_cost
from subunit_geometry import validate as geometry_check
OUT=ROOT/'tmp/phase11'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n');return x
def main():
 normal=sha(ROOT/'tmp/build/release/TestDrive.Slave');verify=sha(ROOT/'tmp/build/verify/TestDrive.Slave')
 m=read(OUT/'release-matrix.json');assert m['status']=='PASS' and len(m['captures'])==20 and m['slave_sha256']==verify
 old=read(ROOT/'tmp/phase8/grip-matrix-matrix.json');prior={(c['car'],c['period'],c['tape']):c for c in old['captures']}
 unchanged=[]
 for c in m['captures']:
  d=OUT/c['name'];assert byte_check(d)['status']=='PASS';assert timing_check(d)==c['timing'];assert units_check((d/'code.bin').read_bytes(),expected_count=668)['status']=='PASS'
  p=prior[c['car'],c['period'],c['tape']]
  for key in ['peak_mph','end_position','end_x','x_range','gears','timing']:assert c[key]==p[key],(c['name'],key,c[key],p[key])
  unchanged.append(c['name'])
 pairs={}
 for name,a,b,rng in [('crosscpu-demo','demo-a500','demo-a1200',True),('crosscpu-route','route-a500','release-car0-p5-route',False),('slow-drawing','slow-a1200','release-car0-p2-route',False)]:
  result=compare(OUT/a,OUT/b,require_rng=rng);assert result['status']=='PASS';pairs[name]=write(OUT/(name+'.json'),result)
 events={n:police_check(OUT/('events-'+n)) for n in ['a500','a1200']}
 costs={};budgets={}
 for n in [0,1000,1600]:
  d=OUT/f'normal-cost-{n}';assert sha(d/'slave.slave')==normal;costs[n]=render_cost(d);budgets[n]=budget_check(d)
 fps={}
 for machine in ['a500','a1200','a1200-030']:
  rows=[]
  for arm in ['off','on']:
   d=OUT/f'matched-{machine}-{arm}';assert sha(d/'slave.slave')==normal;assert byte_check(d)['status']=='PASS'
   start=read(d/'start-state.json');assert (start['race_car'],start['mode'],start['stage'],start['pos'],start['speed'],start['gear'],start['frames'])==(0,1,3,30*65536,0,0,0)
   windows=[read(d/f'window-{i}/swaps.json') for i in range(2)]
   assert all(w['fields']==1000 and w['presentations']==sum(w['marker_counts']) for w in windows)
   rows.append([w['window_fps'] for w in windows])
  fps[machine]={'off':rows[0],'on':rows[1]}
 for version in ['19.2','20.0']:
  for arm in ['off','on']:
   d=OUT/f'whd-{version}-{arm}';assert sha(d/'slave.slave')==normal;assert byte_check(d)['status']=='PASS';assert (d/'quit.png').is_file();assert read(d/'runtime.json')['whdload_sha256']==read(OUT/'build-runtime.json')[version]['sha256']
 for name in ['verify-disabled','zero-off','zero-on','downhill']:
  assert sha(OUT/name/'slave.slave')==verify;assert byte_check(OUT/name)['status']=='PASS'
 for name in ['audit.json','identification.json','checker-controls.json','render-units.json','projection-fps.json','sideways.json','quit-review.json']:
  assert read(OUT/name)['status']=='PASS',name
 zero=read(OUT/'zero.json');assert all(x['rows']>0 and not x['mismatches'] for x in zero.values())
 geometry_check(OUT/'downhill/view-0')
 pkg=read(ROOT/'tmp/dist/phase11/manifest.json');assert pkg['status']=='PASS' and pkg['slave_sha256']==normal
 assert (ROOT/'tmp/dist/phase11/TestDrive.slave').read_bytes()==(ROOT/'tmp/build/release/TestDrive.Slave').read_bytes()
 for directory in [ROOT/'tmp/dist/phase11',ROOT/'tmp/dist/overlay-cache-ab']:
  for line in (directory/'SHA256SUMS').read_text().splitlines():
   digest,name=line.split('  ',1);assert sha(directory/name)==digest,name
 result=dict(status='PASS',scope='PAL local beta regression; real A1200/68040 deferred, NTSC unvalidated, publication not authorized',normal_sha256=normal,verify_sha256=verify,car_arms=20,handling_identical_to_phase8=unchanged,comparisons=pairs,events=events,render_costs=costs,simulation_budgets=budgets,normal_fps=fps,normal_fps_scope='Matched native demo car/stage/start; subsequent original and fixed-time simulation trajectories/RNG can differ. Isolated projection no-loss gate is separate.',whdload=['19.2','20.0'],archives=pkg)
 write(OUT/'acceptance.json',result)
 paths=[]
 for directory in [OUT,ROOT/'tmp/dist/phase11']:
  for p in directory.rglob('*'):
   if not p.is_file() or p.name=='acceptance-manifest.json':continue
   if directory==OUT and any(x.startswith('package') for x in p.relative_to(OUT).parts):continue
   paths.append(p)
 paths += list((ROOT/'tools').glob('release_*'))+[Path(__file__)]+list((ROOT/'src').glob('*.s'))+list((ROOT/'src').glob('*.i'))
 write(OUT/'acceptance-manifest.json',{'files':{str(p.relative_to(ROOT.parents[1])):sha(p) for p in sorted(set(paths))}})
 print(json.dumps(dict(status='PASS',car_arms=20,normal_fps=fps,render_costs=costs),indent=2))
if __name__=='__main__':main()
