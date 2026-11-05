#!/usr/bin/env python3
"""Audit the accepted phase-8 artifacts without rerunning the emulator."""
import hashlib,json,re,shutil
from pathlib import Path
from harness import ROOT
from check_disabled import check as bytes_check
from check_timing import check as timing_check
from check_units import check as units_check
from check_police import check as police_check
from compare_simulation_demo import compare
from audit_simulation import ranges, originals, validate
from phase8_math import vectors
OUT=ROOT/'tmp/phase8';SOURCE=ROOT/'src'
def read(p):return json.loads(p.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def passed(p):
 r=read(p);assert r['status']=='PASS',p;return r
manifest={}
def pin(p):
 assert p.is_file(),p
 manifest[str(p.relative_to(ROOT.parents[1]))]=sha(p)
 return p
report={'status':'PASS','scope':'Phase 8 PAL emulator beta; hardware deferred and NTSC unvalidated','requirements':{}}
# Final binaries are exactly the tested functional binaries plus version text.
for n in ['TestDrive.slave','TestDrive-verify.slave']:
 new=ROOT/'tmp/build'/n;old=OUT/'grip-snapshot'/n
 assert new.read_bytes().count(b'1.6b')==3
 assert new.read_bytes().replace(b'1.6b',b'1.5b')==old.read_bytes()
 pin(new);pin(old)
# Match every native expected vector with the independent exact integer model.
s=(SOURCE/'simulation-verify.s').read_text()
for fn,expected in vectors().items():
 block=s.split('verify_vectors_'+fn+':\n',1)[1].split('\nverify_vectors_',1)[0]
 actual=[tuple(map(int,line.split(','))) for line in re.findall(r'^    dc.l (.+)$',block,re.M)]
 assert actual==expected,fn
assert 22+2*sum(map(len,vectors().values()))==668
rs=ranges();validate(rs,originals());assert len(rs)==66
matrix=passed(OUT/'grip-matrix-matrix.json');assert len(matrix['captures'])==20
assert {(c['car'],c['period'],c['tape']) for c in matrix['captures']}=={(c,p,t) for c in range(5) for p in (2,5) for t in ('straight','route')}
for c in matrix['captures']:
 p=OUT/c['name'];assert sha(p/'slave.slave')==matrix['slave_sha256']
 assert timing_check(p)==c['timing'];assert bytes_check(p)['status']=='PASS'
 assert units_check((p/'code.bin').read_bytes(),expected_count=668)['status']=='PASS'
 assert int.from_bytes((p/'states/frame-0000.bin').read_bytes()[60:62],'big')==c['car']
 for f in ['capture.json','machine.json','slave.slave','slave.lst','states/samples.json','units.json','handling.json']:pin(p/f)
report['requirements']['1_arithmetic_period_budget']=['668 native assertions and exact model vectors','grip-budget-a500/budget.json','grip-budget-a1200/budget.json']
report['requirements']['2_rates_geometry_decisions']=['20 car/period/tape arms','grip-real-clamp-a1200/result.json','grip-real-negative-clamp-a1200-centred/result.json','grip-slow-route-comparison.json']
report['requirements']['3_clock_results']=['per-field matrix timing','grip-manual-a1200/neutral/result.json','grip-stage-results-a1200/result.json','grip-stage-results-a1200/stage-reset.json']
report['requirements']['4_events_rng']=['grip-natural-crash-a1200-centred/result.json','grip-natural-police-a1200/police-check.json','grip-final-events-a1200','grip-final-demo-comparison.json']
report['requirements']['5_gating_audit']=['66 declarations audited','grip-normal-disabled-a1200','grip-verify-allzero-a1200','grip-live-reload-a1200/byte-check.json']
report['requirements']['6_fidelity_cars_independence']=['grip-native-p5-equivalence.json','grip-handling-comparison.json','grip-crosscpu-route-comparison.json','grip-slow-route-comparison.json','grip-final-demo-comparison.json']
for a,b,nonempty,filename in [
 ('grip-final-demo-a500','grip-final-demo-a1200',True,'grip-final-demo-comparison.json'),
 ('grip-crosscpu-route-a500','grip-matrix-car0-p5-route',False,'grip-crosscpu-route-comparison.json'),
 ('grip-final-route-a1200','grip-final-slow-route-a1200-retry',False,'grip-slow-route-comparison.json')]:
 result=compare(OUT/a,OUT/b,require_rng=nonempty);assert result['status']=='PASS';assert result==read(OUT/filename)
 for n in (a,b):
  p=OUT/n
  assert bytes_check(p)['status']=='PASS'
  assert units_check((p/'code.bin').read_bytes(),expected_count=668)['status']=='PASS'
  for f in ['capture.json','machine.json','slave.slave','slave.lst','states/samples.json','code.bin','end/code.bin','end/chip.bin']:pin(p/f)
for n in ['grip-normal-disabled-a1200','grip-verify-allzero-a1200','final-normal-enabled-a1200','grip-live-reload-a1200']:
 assert bytes_check(OUT/n)['status']=='PASS'
for n in ['grip-final-events-a1200','grip-natural-police-a1200']:assert police_check(OUT/n)['status']=='PASS'
for name in ['grip-native-p5-equivalence.json','grip-comparator-controls.json','grip-real-clamp-a1200/result.json','grip-real-negative-clamp-a1200-centred/result.json','grip-natural-crash-a1200-centred/result.json','grip-stage-results-a1200/result.json','grip-stage-results-a1200/stage-reset.json','grip-manual-a1200/neutral/result.json','final-audit.json','final-inventory.json']:
 passed(pin(OUT/name))
for n in ['grip-budget-a500','grip-budget-a1200']:
 r=read(pin(OUT/n/'budget.json'));assert all(v['status']=='PASS' and v['max_period_percent']<100 for v in r.values())
for name in ['grip-handling-comparison.json','version-equivalence.json','final-capture-checks.json']:
 pin(OUT/name)
# Preserve current source/build snapshots and pin relevant local tools/docs.
dest=OUT/'accepted-1.6b';dest.mkdir(exist_ok=True)
for p in [*SOURCE.glob('simulation*'),SOURCE/'TestDriveHD.s',SOURCE/'Makefile_windows.mak',SOURCE/'ENHANCEMENT_PLAN.md',SOURCE.parent/'readme',* (ROOT/'tmp/build').glob('TestDrive*.slave*')]:
 if p.name not in ['TestDrive.slave','TestDrive.slave.lst','TestDrive-verify.slave','TestDrive-verify.slave.lst'] and p.parent==ROOT/'tmp/build':continue
 shutil.copyfile(p,dest/p.name);pin(dest/p.name)
for p in (ROOT/'tools').glob('*.py'):pin(p)
for n in ['phase8.md','development.md','open-work.md']:pin(ROOT/'docs'/n)
for name in ['grip-manual-a1200/normal-quit.png','grip-stage-results-a1200/text-2.png','grip-stage-results-a1200/text-4.png','final-normal-enabled-a1200/end.png']:
 pin(OUT/name)
# Immutable original inputs and hardware handoff pair.
for mf,base in [(ROOT/'manifest/inputs.sha256',ROOT),(ROOT/'tmp/dist/overlay-cache-ab/SHA256SUMS',ROOT/'tmp/dist/overlay-cache-ab')]:
 for line in mf.read_text().splitlines():
  digest,name=line.split('  ',1);assert sha(base/name)==digest,name
 pin(mf)
(OUT/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');pin(OUT/'acceptance.json')
(OUT/'acceptance-manifest.json').write_text(json.dumps({'files':manifest},indent=2)+'\n')
print(json.dumps({'status':'PASS','matrix_arms':20,'native_assertions':668,'range_declarations':66,'pinned_files':len(manifest)}))
