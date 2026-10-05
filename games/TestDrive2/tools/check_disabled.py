#!/usr/bin/env python3
"""Verify a CUSTOM2=0 (enhanced framerate off) capture retains original v1 bytes at every simulation patch.
CUSTOM3's shared reproducibility RNG patch is excluded. No game bytes are emitted.
"""
import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--base',type=lambda s:int(s,0),default=0xc00000)
p.add_argument("--render-only",action="store_true",help="check only sub-unit rendering ranges ")
a=p.parse_args()
root=Path(__file__).resolve().parents[1]
original=(root/'tmp/game/TestDrive2/data/duel').read_bytes()
assert len(original)==108868,'requires duel v1'
meta=json.loads((a.capture/'state/metadata.json').read_text())
code=meta['code_base']-a.base
mem=(a.capture/'code.bin').read_bytes()
cases=0
lines=[] if a.render_only else (root/'whdload/simulation-patches.i').read_text().splitlines()
lines += [line for line in (root/'whdload/TestDrive2HD.s').read_text().splitlines()
          if 'render_subunit_' in line and 'PL_' in line]
for line in lines:
    m=re.search(r'PL_(PSS|PS|P|NOP|W|L)\s+\$([0-9a-f]+),([^;]+)',line)
    if not m:continue
    kind,start,args=m.groups();start=int(start,16)
    if start in (0xe9f0,0xe9f2):continue
    if kind=='PSS':size=6+int(args.split(',')[1])
    elif kind in ('PS','P'):size=6
    elif kind=='NOP':size=int(args)
    else:size={'W':2,'L':4}[kind]
    assert mem[code+start:code+start+size]==original[40+start:40+start+size],f'optional patch still active at {start:05x}'
    cases+=1
print(f'Enhanced framerate off: {cases} patch ranges retain original v1 instructions')
