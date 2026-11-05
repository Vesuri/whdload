#!/usr/bin/env python3
"""Validate the required measurement evidence without launching another emulator."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);matrix=root/'matrix'
cpus=['a500-fast','a1200-fast','a1200-030','a1200-040','a1200-060']
required=[('takeoff',c) for c in cpus]+[(s,c) for s in ('hover','combat') for c in ('a500-fast','a1200-060')]
report={'windows':{},'repeated_ticks':[]};slave_hashes=set();source_hashes=set();module_hashes=set()
mission=(root/'state-1/initial/mission.bin').read_bytes()[:0x94]
for scene,cpu in required:
 p=matrix/scene/cpu;r=json.loads((p/'result.json').read_text());v=json.loads((p/'provenance.json').read_text());L=json.loads((p/'layout.json').read_text())
 assert r['end_vbl']-r['start_vbl']==500
 assert r['frames']>0 and r['ticks_per_second']>0
 assert len(r['frame_log'])==r['frames']
 assert all(a[0]<b[0] and a[2]^b[2]==1 for a,b in zip(r['frame_log'],r['frame_log'][1:]))
 slave_hashes.add(v['hashes']['runtime_slave']);source_hashes.add(v['hashes']['source']);module_hashes.add(v['hashes']['verify_module'])
 assert (p/'initial/mission.bin').read_bytes()[:0x94]==mission
 checks={'fps':r['fps'],'ticks_per_second':r['ticks_per_second'],'pacing':r['pacing']}
 if scene=='hover':
  a=(p/'initial/h6.bin').read_bytes()[0x3b88:];b=(p/'final/h6.bin').read_bytes()[0x3b88:]
  fields=lambda x:[int.from_bytes(x[i:i+n],'big') for i,n in ((0,2),(2,2),(28,2),(42,2),(54,1),(55,1),(57,1))]
  assert fields(a)==fields(b);assert fields(a)[2]>0 and fields(a)[3:6]==[0,0,0]
  checks['stationary_airborne_endpoints']=fields(a)
 if scene=='combat':
  mem=(p/'initial/fast.bin').read_bytes();off=L['address']-0x200000+68
  assert int.from_bytes(mem[off:off+4],'big')==1
  checks['combat_fixture_applied']=True
 report['windows'][scene+'/'+cpu]=checks
assert len(slave_hashes)==len(source_hashes)==len(module_hashes)==1
assert hashlib.sha256((root.parent/'build/verify/Gunship.Slave').read_bytes()).hexdigest() in slave_hashes
source=Path(__file__).resolve().parents[1]/'src'
assert hashlib.sha256((source/'GunshipHD.s').read_bytes()).hexdigest() in source_hashes
assert hashlib.sha256((source/'verify.i').read_bytes()).hexdigest() in module_hashes
for i in range(3):
 r=json.loads((root/f'repeatability-{i}.json').read_text());assert all(v['equal'] for v in r.values())
 assert 'fast.bin' in r;report['repeated_ticks'].append(100+i)
negative=json.loads((root/'negative-control.json').read_text());assert not negative['player_without_tick']['equal']
assert (root/'mission-delay/initial/mission.bin').read_bytes()[:0x94]==mission
assert (root/'mission-seed2/initial/mission.bin').read_bytes()[:0x94]!=mission
report.update(mission_cpu_and_dwell_invariance=True,seed_change_control=True,negative_tick_control=True,slave_sha256=next(iter(slave_hashes)))
(root/'acceptance.json').write_text(json.dumps(report,indent=2));print('PASS:',len(required),'windows; three repeated whole-RAM ticks; seed/dwell and negative controls')
