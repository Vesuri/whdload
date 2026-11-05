#!/usr/bin/env python3
"""Collect completed phase-10 reports and pin their exact builds and evidence."""
import hashlib,json,shutil
from pathlib import Path
from harness import ROOT
base=ROOT/'tmp/phase10';repo=ROOT
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['matrix4-'+p+'-'+a for p in ['a500','a1200','a1200-030'] for a in ['off','on']]
names+=['final-zero-off','final-zero-on','final-downhill','final-cost-demo','integer-cost-late','final-normal-off','final-normal-on']
for n in names:
 p=base/n;m=read(p/'capture.json');built=ROOT/'tmp/build'/('TestDrive.slave' if 'normal' in n else 'TestDrive-verify.slave')
 assert m['slave_sha256']==sha(p/'slave.slave')==sha(built),(n,'build differs')
 if 'normal' not in n:assert read(p/'units.json')['assertions']==668
assert read(base/'fps-comparison.json')['status']=='PASS'
assert read(base/'final-units.json')==dict(status='PASS',assertions=1421,failures=0)
assert all(not x['mismatches'] for x in read(base/'final-zero.json').values())
assert all(not x['road_errors'] and x['changed_cars'] for x in read(base/'final-downhill.json').values())
for n in ['final-cost-demo','integer-cost-late']:
 r=read(base/(n+'.json'));assert r['main_calls']>0 and r['fields']==50 and r['percent']<=3
for a in ['off','on']:assert read(base/('final-normal-'+a+'-bytes.json'))['status']=='PASS'
assert read(base/'integer-render-audit.json')['status']=='PASS'
assert read(base/'checker-negative-controls.json')['status']=='PASS'
accepted=base/'accepted';accepted.mkdir(exist_ok=True)
for n in ['TestDrive.slave','TestDrive.slave.lst','TestDrive-verify.slave','TestDrive-verify.slave.lst']:shutil.copyfile(ROOT/'tmp/build'/n,accepted/n)
report=dict(status='PASS',version='1.8b',captures=names,renderer_assertions=1421,simulation_assertions=668,
 fps=read(base/'fps-comparison.json')['machines'],cost={n:read(base/(n+'.json')) for n in ['final-cost-demo','integer-cost-late']},
 zero=read(base/'final-zero.json'),downhill=read(base/'final-downhill.json'),crossing=read(base/'crossing-fixed.json'),
 sideways=read(base/'sideways-demo.json'),limitations=['PAL emulator beta; real A1200/68040 deferred; NTSC unvalidated',
 'Crossing and mountain captures precede the exact cache and slope fast paths; their projection formulas are unchanged.',
 'CPU and FPS are finite-window samples, not universal worst-case or whole-race bounds.',
 'Full release/old-new WHDLoad regression and packaging remain phase 11.'])
(base/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n')
files=[]
for n in names+['crossing-before-fixed','crossing-after-fixed','sideways-demo','final-quarter-hill','final-quarter-curve']:
 files.extend(p for p in (base/n).rglob('*') if p.is_file())
files.extend(p for p in accepted.iterdir() if p.is_file())
files.extend(base.glob('*.json'))
files.extend(p for p in (repo/'src').iterdir() if p.is_file())
files.append(repo/'release/readme')
files.extend(p for p in (ROOT/'tools').glob('*.py'))
files.extend([ROOT/'tools/build.sh',ROOT/'tools/final_render_checks.sh'])
files.extend((ROOT/'manifest').glob('phase10-*'))
files.extend(ROOT/'docs'/n for n in ['phase10.md','development.md','internals.md','open-work.md'])
manifest={str(p.relative_to(repo)):sha(p) for p in sorted(set(files)) if p.name not in ['acceptance-manifest.json','acceptance-summary.json']}
(base/'acceptance-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(status='PASS',files=len(manifest),normal_sha256=sha(accepted/'TestDrive.slave'),verify_sha256=sha(accepted/'TestDrive-verify.slave')),indent=2))
