#!/usr/bin/env python3
"""Check two ordinary replays per supported CPU; retain state gates separately."""
import os,sys,json
from pathlib import Path
from replay_flight import ROOT,run
from compare_flight import compare
out=Path(sys.argv[1]).resolve();os.chdir(ROOT);out.mkdir(parents=True);summary={}
for cpu in ['040','020','030','060']:
 v=dict(executable='TFX' if cpu=='020' else 'tfx.020',custom3=0 if cpu=='020' else 3,custom4=18,swap=0x18a6 if cpu=='020' else 0x19fc,extra_args='--uae_fpu_no_unimplemented=true' if cpu=='040' else '')
 for i in [1,2]:run(cpu,out/f'{cpu}-{i}',out/f'{cpu}-seed',variant=v)
 r=compare(out/f'{cpu}-1',out/f'{cpu}-2');(out/f'{cpu}-comparison.json').write_text(json.dumps(r,indent=2))
 baseline=ROOT/f'tmp/step7/regression-shared/{cpu}-1'
 visual=all(p.read_bytes()==(baseline/p.name).read_bytes() for p in (out/f'{cpu}-1').glob('swap-*.png'))
 bases=json.loads((out/f'{cpu}-1/segments.json').read_text())
 assert all(a>=0x40000000 for a in bases) if cpu=='040' else True
 if cpu in ['030','060']:assert all(a<0x200000 for a in bases[1:])
 summary[cpu]={k:r[k] for k in ['raw_identical','clock_relative_identical','screenshots_identical','clock_origin_delta']}
 summary[cpu]['step7_screenshots_identical']=visual
 (out/'summary.json').write_text(json.dumps(summary,indent=2));print(cpu,summary[cpu],flush=True)
assert all(r['screenshots_identical'] for r in summary.values())
