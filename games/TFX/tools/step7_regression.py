#!/usr/bin/env python3
"""Functional replay matrix, strict 040 MMU, and preserved 020 clock waiver."""
import os,json,sys
from pathlib import Path
from replay_flight import ROOT,run
from compare_flight import compare
out=Path(sys.argv[1]).resolve();os.chdir(ROOT);out.mkdir(parents=True,exist_ok=True)
results={}
for cpu in ['040','020','030','060']:
 v=dict(executable='TFX' if cpu=='020' else 'tfx.020',custom3=0 if cpu=='020' else 3,custom4=18,swap=0x18a6 if cpu=='020' else 0x19fc,extra_args='--uae_fpu_no_unimplemented=true' if cpu=='040' else '')
 seedroot=Path(os.environ['SEED_ROOT']) if 'SEED_ROOT' in os.environ else out
 for i in [1,2]:run(cpu,out/f'{cpu}-{i}',seedroot/f'{cpu}-seed',variant=v)
 r=compare(out/f'{cpu}-1',out/f'{cpu}-2');(out/f'{cpu}-comparison.json').write_text(json.dumps(r,indent=2))
 results[cpu]={k:r[k] for k in ['raw_identical','clock_relative_identical','screenshots_identical','clock_origin_delta']}
 (out/'summary.json').write_text(json.dumps(results,indent=2));print(cpu,results[cpu],flush=True)
assert all(r['raw_identical'] if cpu in ['040','060'] else r['clock_relative_identical'] for cpu,r in results.items())
