#!/usr/bin/env python3
"""Check event ownership and early acceleration for the native timing input fixtures."""
import argparse
import json
from pathlib import Path
import re
import struct
from coverage_status import fixture
from timing_report import input_state, NAMES

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
a=p.parse_args()
for root in a.captures:
    config=json.loads((root/'configuration.json').read_text())
    assert any(x in config['WHD_ARGS'] for x in ('CUSTOM5=7','CUSTOM5=8'))
    before=input_state(root/'code.bin');after=input_state(root/'final-code.bin')
    assert before and after
    assert after['overflow']==0,'Input events overflowed the queue'
    assert after['read']==after['write'],'Input events remain unconsumed at the endpoint'
    assert after['produced']==after['consumed']
    if 'CUSTOM5=7' in config['WHD_ARGS']:
        expected_events=6 if after['version']==2 else 3
        assert after['produced']==expected_events,'Expected button edges and, for V2, three mouse deltas'
    game=int((root/'game-base.txt').read_text(),0)
    chip=(root/'chip.bin').read_bytes()
    target=struct.unpack_from('>H',chip,game+0xa6e+0x454)[0]
    speed=struct.unpack_from('>H',chip,game+0xa6e+0x194)[0]
    epoch=fixture(root/'code.bin')['epoch']
    # Input tape compares before incrementing the native VBL count; capture follows it.
    throttle=(epoch+11)*4
    cutoff=(epoch+90)*4  # Stay clear of braking, whose independent cadence starts at 100.
    observed=[]
    for field,values in re.findall(r'^PDTIME_EVENT (-?\d+) 0xd058 (.+)$',(root/'swaps-gdb.txt').read_text(),re.M):
        row=dict(zip(NAMES,[int(field)]+list(map(int,values.split()))))
        observed.append(row['speed'])
    expected=[]
    clock=before['clock']
    while clock<cutoff:
        if clock>=throttle:speed+=(target-speed)//8
        expected.append(speed)
        clock+=18
    assert len(expected)>=15 and len(observed)>=len(expected)
    assert observed[:len(expected)]==expected,(root.name,observed[:len(expected)],expected)
    if after['version']==2 and 'CUSTOM5=7' in config['WHD_ARGS']:
        log=(root/'swaps-gdb.txt').read_text()
        axes=[]
        for values in re.findall(r'^PDINPUT_EVENT -?\d+ 0xd058 (.+)$',log,re.M):
            tick,consumed,mode,active,joy,x,y=map(int,values.split())
            expected_x=sum(delta for field,delta in ((161,40),(191,-80),(221,40))
                           if tick>=(epoch+field)*4)
            expected_consumed=sum(tick>=(epoch+field)*4 for field in (11,101,151,161,191,221))
            assert (mode,active,joy)==(0,1,0),'Wrong logical input mode/ownership'
            assert (x,y)==(expected_x&0xffff,0),'Mouse delta applied at wrong logical time or overwritten'
            assert consumed==expected_consumed,'Input event applied at wrong logical time'
            axes.append(tick)
        assert len(axes)>=50 and all(b-a==18 for a,b in zip(axes,axes[1:])), 'Missing or repeated logical control updates'
        for values in re.findall(r'^PDINPUT_EVENT -?\d+ 0xccee (.+)$',log,re.M):
            assert int(values.split()[3])==0,'Historical control state leaked outside its update'
        print(f'{root.name}: {len(axes)} mouse-state updates match the independent timestamp/delta oracle')
    print(f'{root.name}: {len(expected)} logical acceleration updates match timestamped input; {after["consumed"]} events consumed; no overflow or pending events')
