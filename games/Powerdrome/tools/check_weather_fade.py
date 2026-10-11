#!/usr/bin/env python3
"""Validate the two-transition directed fade fixture and native gear commits.

Checks logical cadence/state and CPU equality, not palette pixels, natural weather,
or pause/pit/restart lifecycle handling.
"""
import argparse
from pathlib import Path
import re
import struct
from weather_fade_state import locate, parse_values, snapshot


def check(root):
    chip=(root/'final-chip.bin').read_bytes()
    code=(root/'final-code.bin').read_bytes()
    game=int((root/'game-base.txt').read_text(),0)
    base=int((root/'dump-base.txt').read_text(),0)
    address=locate(chip,code,game,base)
    assert address is not None
    tag=code.find(b'PDWFTS01',address-base+48,address-base+4096)
    assert tag>=0, 'Missing directed fade fixture'
    phase,positive_start,negative_start=struct.unpack_from('>3I',code,tag+8)
    assert phase==2
    first=snapshot(root)
    last=snapshot(root,True)
    assert first['positive']==first['negative']==0
    assert (last['positive'],last['negative'],last['gears'])==(15,15,2)
    assert last['expected']==last['transition']==last['active']==last['pending']==0
    events=[(int(field),int(off,16),parse_values(values)) for field,off,values in re.findall(
        r'^PDWFADE_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',
        (root/'swaps-gdb.txt').read_text(),re.M)]
    pending=None
    presented=0
    for _,off,state in events:
        if off==0xbd1a:
            assert pending is None, 'Missing prior presentation return'
            if state['forecast']>0:
                pending=state
        elif off==0xbd58 and pending is not None:
            assert all(state[k]==v for k,v in pending.items() if k not in ('pending','draws')), 'Palette presentation changed logical fade state'
            assert state['pending']==0
            assert state['draws']==pending['draws']+int(pending['pending']!=0)
            presented+=int(pending['pending']!=0)
            pending=None
    assert pending is None, 'Unfinished observed palette presentation'
    assert presented==last['draws']-first['draws'] and presented>0
    rows=[]
    for direction,start,first_delay,period in (
            ('positive',positive_start,192,280),('negative',negative_start,236,232)):
        for n in range(1,16):
            samples=[s for _,off,s in events if off==0xccee and s[direction]==n
                     and s['start']==start]
            assert samples, f'Missing {direction} step {n}'
            s=samples[0]
            clock=start+first_delay+(n-1)*period
            transition=(15-n if direction=='positive' else n-15)&65535
            assert s['last']==clock, f'Wrong {direction} step deadline at {n}'
            assert s['transition']==s['expected']==transition
            assert s['active']==(n<15)
            assert s['gears']==(int(n==15) if direction=='positive' else 1+int(n==15))
            rows.append((direction,n,s['last']-start,transition))
    assert negative_start==positive_start+192+14*280+200
    gears=[]
    for entry,ret,table in ((0x8a4c,0x8a5e,0x2068),(0x8a8e,0x8aa0,0x204c)):
        before=[s for _,off,s in events if off==entry]
        after=[s for _,off,s in events if off==ret]
        assert len(before)==len(after)==1, 'Missing/duplicate native gear commit'
        assert before[0]['transition']==after[0]['transition']==0
        track=before[0]['track']
        expected=struct.unpack_from('>H',chip,game+table+2*track)[0]
        assert after[0]['track']==track and after[0]['gear']==expected
        gears.append(expected)
    print(f'{root.name}: all 30 fade steps and two native gear commits verified; gear targets={gears}')
    print(f'  Positive 20560 ms; negative 17420 ms; palette publications drawn={last["draws"]-first["draws"]}; no pending fade at endpoint')
    return rows,gears


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures',nargs='+',type=Path)
    results=[check(root) for root in p.parse_args().captures]
    assert all(r==results[0] for r in results), 'Logical fades/gear targets differ across captures'
    print('All supplied captures match; natural episode and palette/lifecycle validation remain separate.')
