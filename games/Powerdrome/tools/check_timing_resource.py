#!/usr/bin/env python3
"""Check native fuel arithmetic and compare each logical resource update across CPUs."""
import argparse
import json
import struct
from pathlib import Path
from coverage_status import fixture
from timing_report import input_state

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
a=p.parse_args()
def signed16(value): return ((value&65535)^32768)-32768
runs=[]
configs=[]
for root in a.captures:
    config=json.loads((root/'configuration.json').read_text())
    assert any(route in config['WHD_ARGS'] for route in ('CUSTOM5=7','CUSTOM5=8','CUSTOM5=9'))
    configs.append(config['WHD_ARGS'].split('CUSTOM5=')[1].split()[0])
    epoch=fixture(root/'code.bin')['epoch']*4
    game=int((root/'game-base.txt').read_text(),0)
    initial_fuel=struct.unpack_from('>H',(root/'chip.bin').read_bytes(),game+0xa6e+0x1ba)[0]
    initial_tick=input_state(root/'code.bin')['clock']-epoch
    rows=[]; tick=None; previous=initial_fuel
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        parts=line.split()
        if len(parts)<3:continue
        if parts[0]=='PDINPUT_EVENT' and parts[2]=='0xd9a0':
            tick=int(parts[3])-epoch
        elif parts[0]=='PDRESOURCE':
            field,speed,before,scale,boost,gear,target,engine,disabled,after=map(int,parts[1:])
            assert tick is not None and engine and not disabled, 'Route no longer covers running eligible resource updates'
            # Native MULS followed by two word shifts intentionally uses the low word.
            debit=max(1,signed16(signed16(speed)*signed16(scale))>>10)
            debit*=1+bool(boost)+(gear!=target)
            assert before>debit, 'Fuel-depletion route requires a separate eligibility oracle'
            assert after==before-debit, (root.name,tick,before,after,debit)
            if previous is not None: assert before==previous, 'Fuel changed outside the logical resource call'
            rows.append((tick,speed,before,after,boost,gear,target))
            previous=after;tick=None
    assert rows and rows[0][0]==initial_tick, 'First owed resource update was skipped'
    if configs[-1]=='9': assert any(row[4] for row in rows), 'Joystick route did not exercise boost consumption'
    assert len(rows)>=50 and all(b[0]-a[0]==18 for a,b in zip(rows,rows[1:])), 'Missing or repeated resource updates'
    runs.append(rows)
    print(f'{root.name}: {len(rows)} logical fuel updates match native arithmetic and form one continuous state sequence')
assert len(set(configs))==1, 'Compare the same input route across captures'
length=min(map(len,runs))
assert max(map(len,runs))-length<=1, 'Logical windows differ beyond one endpoint update'
for root,rows in zip(a.captures[1:],runs[1:]):
    for expected,actual in zip(runs[0][:length],rows[:length]):
        assert expected==actual,(root.name,'first different logical resource update',expected,actual)
if len(runs)>1:print(f'{length} complete common resource updates match across {len(runs)} captures')
