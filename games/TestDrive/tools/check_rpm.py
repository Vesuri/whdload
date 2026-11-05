#!/usr/bin/env python3
"""Validate retained tachometer regression evidence; no emulator writes."""
import json,re
from pathlib import Path
from harness import ROOT,sha
from audit_simulation import ranges,originals,validate
from check_disabled import check as installed
from check_units import check as units
from check_render_units import check as render_units
out=ROOT/'tmp/rpm-needle';report={'status':'PASS'}
rs=ranges();report['audit']={'ranges':len(rs),'incoming':validate(rs,originals())};assert len(rs)==84
report['porsche_state_comparisons']=[]
for a,b in [('neutral-porsche-on','final-neutral-porsche-on'),('before-porsche-on','final-gear-porsche-on')]:
 x=json.loads((out/a/'states.json').read_text());y=json.loads((out/b/'states.json').read_text());assert x==y,(a,b)
 report['porsche_state_comparisons'].append({'before':a,'after':b,'identical_samples':len(x),'final_rpm':y[-1]['rpm'],'event':y[-1]['event']})
report['cars']=[]
for car,name,limit in [(0,'porsche-on',7000),(1,'ferrari-off',10000),(2,'lotus-on',7000),(3,'countach-on',9000),(4,'vette-on',0)]:
 p=out/('final-neutral-'+name);s=json.loads((p/'states.json').read_text());actual=int.from_bytes((p/'display-limit.bin').read_bytes(),'big');assert actual==limit and s[-1]['event']==1 and max(x['rpm'] for x in s)>limit
 report['cars'].append({'car':car,'capture':p.name,'limit':limit,'maximum_observed_rpm':max(x['rpm'] for x in s),'metadata_sha256':sha(p/'metadata.json')})
p=out/'units-run';m=json.loads((p/'capture.json').read_text());ram=(p/'code.bin').read_bytes();syms={n:int(a,16) for n,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
o=m['regions']['td']+0x6390-m['base'];slave=int.from_bytes(ram[o+2:o+6],'big')-syms['overlay_unload_end']
def word(n):
 o=slave+syms[n]-m['base'];return int.from_bytes(ram[o:o+4],'big')
assert word('rpm_unit_count')==327680 and word('rpm_unit_failures')==0
report['exhaustive']={'cases':word('rpm_unit_count'),'failures':word('rpm_unit_failures')}
report['simulation_units']=units(ram,668);report['render_units']=render_units(p/'code.bin')
report['normal_smokes']=[]
for name in ['normal-off','normal-on']:
 p=out/name;r=installed(p);assert sha(p/'slave.slave')==sha(ROOT/'tmp/dist/2.0b/TestDrive.slave');assert (p/'quit.png').exists()
 report['normal_smokes'].append({'name':name,'installed_ranges':len(r['ranges']),'slave_sha256':sha(p/'slave.slave'),'quit_screenshot_sha256':sha(p/'quit.png')})
report['sources']={p.name:sha(p) for p in (ROOT/'src').iterdir() if p.is_file()}
report['tools']={n:sha(ROOT/'tools'/n) for n in ['rpm_capture.py','rpm_smoke.py','rpm_units.py','check_rpm.py','audit_simulation.py','check_disabled.py']}
report['package_manifest_sha256']=sha(ROOT/'tmp/dist/2.0b/manifest.json')
report['slave_sha256']=sha(ROOT/'tmp/dist/2.0b/TestDrive.slave')
for name,expected in [('baseline-1.4-rebuilt','95188df7e59d54ed69d56b0824ab18d461f1a2a5dad01ea58387aba96a0f2b56'),('fixed-1.5b','ca765222b4257e060e684b80581ed45506d8167c98c016c6d088ad066d6750d4')]:assert sha(ROOT/'tmp/dist/overlay-cache-ab'/name/'TestDrive.slave')==expected
(out/'acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['sources','tools','audit']},indent=2))
