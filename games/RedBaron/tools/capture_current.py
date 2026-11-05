#!/usr/bin/env python3
"""Capture a bounded trace at the current paused checkpoint, retaining observer states."""
import argparse,json
from pathlib import Path
import step_log,route_status as r
from profile_flight import command
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--fields',type=int,default=100);a=p.parse_args()
if not 1<=a.fields<=100:raise SystemExit('Use a single 1..100-field chunk')
a.out.mkdir(parents=True,exist_ok=False);out=a.out.resolve()
(out/'before.json').write_text(json.dumps(step_log.collect(),indent=2)+'\n')
for lo,hi in r.memory_regions():r.command(f'gdb dump binary memory {a.out}/memory-{lo:x}.bin {lo:#x} {hi:#x}')
print(command(f'profile {a.fields} {out}/trace.bin'),flush=True)
(out/'after.json').write_text(json.dumps(step_log.collect(),indent=2)+'\n')
