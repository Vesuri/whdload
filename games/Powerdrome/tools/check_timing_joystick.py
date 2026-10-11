#!/usr/bin/env python3
"""Check logical joystick state against timed input and native response arithmetic."""
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
acceleration=[]
for root in a.captures:
    config=json.loads((root/'configuration.json').read_text())
    assert 'CUSTOM5=9' in config['WHD_ARGS']
    initial=input_state(root/'code.bin');final=input_state(root/'final-code.bin')
    assert initial['version']==final['version']==2
    assert final['produced']==final['consumed']==6 and final['overflow']==0
    assert final['read']==final['write'] and not final['control_active']
    game=int((root/'game-base.txt').read_text(),0)
    for filename in ('chip.bin','final-chip.bin'):
        chip=(root/filename).read_bytes()
        assert struct.unpack_from('>H',chip,game+0xa6e+0x422)[0]==0xffff, 'Native menu did not select joystick'
    epoch=fixture(root/'code.bin')['epoch']
    log=(root/'swaps-gdb.txt').read_text()
    x=initial['x']; y=initial['y']; ticks=[]; damped=0
    # Several logical updates may share one physical field: preserve order.
    steering=re.findall(r'^PDSTEER_EVENT (-?\d+) 0xd058 (.+)$',log,re.M)
    steering_rows=iter(steering)
    has_steering=bool(steering)
    saved=struct.unpack_from('>HH',(root/'chip.bin').read_bytes(),game+0xa6e+0x436)
    def signed16(value): return ((value&65535)^32768)-32768
    for observed_field,values in re.findall(r'^PDINPUT_EVENT (-?\d+) 0xd058 (.+)$',log,re.M):
        tick,consumed,mode,active,joy,observed_x,observed_y=map(int,values.split())
        expected_joy=0
        for field,value in ((11,0x81),(101,0x82),(151,0),(161,4),(191,8),(221,0)):
            if tick>=(epoch+field)*4: expected_joy=value
        expected_consumed=sum(tick>=(epoch+field)*4 for field in (11,101,151,161,191,221))
        assert (consumed,mode,active,joy)==(expected_consumed,0xffff,1,expected_joy), 'Incorrect joystick event ownership'
        # Native d26c response on this horizontal-only tape. Fire holds the axes.
        if not joy&0x80:
            step=((175-abs(x))*40)>>8
            if joy&4: x-=step+(x>>2 if x>=0 else 0)
            elif joy&8: x+=step+((-x)>>2 if x<0 else 0)
            y-=y>>3
        x=((x&0xffff)^0x8000)-0x8000
        assert (observed_x,observed_y)==(x&0xffff,y&0xffff), (
            'Native joystick response changed or ran at the wrong cadence',tick,
            (observed_x,observed_y),(x&0xffff,y&0xffff))
        if has_steering:
            steering_field,steering_values=next(steering_rows)
            assert steering_field==observed_field, 'Misordered contact response probe'
            contact,saved_x,saved_y=map(int,steering_values.split())
            assert (saved_x,saved_y)==saved, 'Saved steering changed outside the control response'
            if contact:
                # Native signed MULS/ASR at d05e..d082 overwrites logical
                # axes after this probe, so it affects the next input update.
                x=signed16((signed16(saved_x)*230)>>8)
                y=signed16((signed16(saved_y)*230)>>8)
                damped+=1
            saved=(x&0xffff,y&0xffff)
        ticks.append(tick)
    if has_steering:
        assert (final['x'],final['y'])==(x&0xffff,y&0xffff), 'Unobserved final logical axis mutation'
    assert next(steering_rows,None) is None, 'Unmatched contact response probes'
    assert len(ticks)>=50 and all(b-a==18 for a,b in zip(ticks,ticks[1:]))
    early=[]
    for values in re.findall(r'^PDTIME_EVENT (-?\d+ 0xd058 .+)$',log,re.M):
        parts=values.split(); row=dict(zip(NAMES,[int(parts[0])]+list(map(int,parts[2:]))))
        early.append(row['speed'])
    acceleration.append(early[:19])
    print(f'{root.name}: {len(ticks)} logical joystick updates match native response; six timestamped events, no overflow/debt; {damped} observed contact damping updates')
assert all(seq==acceleration[0] for seq in acceleration), 'Early joystick acceleration differs across captures'
if len(acceleration)>1: print('First 19 joystick acceleration updates match across all captures')
