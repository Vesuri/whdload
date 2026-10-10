#!/usr/bin/env python3
"""Check owed brake events for the timed-input route's one-second brake command."""
import argparse
import json
from pathlib import Path
import re
import struct
from timing_report import samples
from coverage_status import fixture

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
a=p.parse_args()
# Route 7: pressed on PAL field 100, released on 150. The first step is immediate.
# Last held sample is field 149. 70 ms is 14 native clock units; each field is four.
expected=1+((150-100-1)*4)//14
for root in a.captures:
    config=json.loads((root/'configuration.json').read_text())
    assert 'CUSTOM5=7' in config['WHD_ARGS']
    data=(root/'final-code.bin').read_bytes()
    blocks=[struct.unpack_from('>HIII',data,m.start()+8) for m in re.finditer(b'PDBRAK02',data)]
    blocks=[b for b in blocks if b[2]]
    assert len(blocks)==1,'Need one initialized VBL brake diagnostic block'
    active,phase,steps,pending=blocks[0]
    assert (active,phase,steps,pending)==(0,0,expected,0),(root,blocks[0])
    assert fixture(root/'final-code.bin')['done'],'Input fixture must finish'
    rows=samples(root)
    assert rows[-1]['speed']==0,'Brake must stop the ship and remain stopped after release'
    print(f'{root.name}: {steps}/{expected} owed brake events applied; no residual debt; stopped')
