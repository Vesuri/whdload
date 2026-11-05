#!/usr/bin/env python3
"""Verify logical engine decisions/cooling and compare cadence across captures."""
import argparse
from pathlib import Path
import re
import struct
from coverage_status import fixture
from timing_report import input_state

NAMES='clock phase active ticks coolings produced consumed overflow left right damage target engine speed presenting'.split()
def word(value):return ((value&65535)^32768)-32768
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
p.add_argument('--require-failures',action='store_true')
a=p.parse_args();cadences=[]
for root in a.captures:
    epoch=fixture(root/'code.bin')['epoch']*4
    initial=input_state(root/'code.bin')['clock']
    start=None;decision=None;rows=[];failures=0;delivered=[]
    for field,offset,values in re.findall(r'^PDENGINE_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$',(root/'swaps-gdb.txt').read_text(),re.M):
        state=dict(zip(NAMES,map(int,values.split())));off=int(offset,16)
        assert not state['overflow'],'Presentation events overflowed'
        if off==0xd9a0:
            assert not state['active']
            start=state
        elif off==0xde0a:
            assert state['active']
            start=state
        elif off in (0xe0c0,0x10d0c,0x13514):
            kind={0xe0c0:1,0x10d0c:2,0x13514:3}[off]
            if state.get('presenting')==kind:
                assert not state['active'], 'Presentation occurred inside a logical engine update'
                delivered.append(kind)
        elif off==0xdfae:
            assert start and state['active'] and state['clock']==start['clock']
            expected={key:start[key] for key in ('left','right','damage','target','engine')}
            count=0
            for key,bit in (('left',2),('right',1)):
                if not expected['damage']&bit and expected[key]>=225:
                    expected[key]=225;expected['damage']|=bit
                    expected['target']=word(expected['target'])>>1
                    count+=1
            if expected['damage']&3==3:expected['engine']=0
            assert all(state[key]==value for key,value in expected.items()),(root.name,'engine decision',start,state,expected)
            assert state['produced']-start['produced']==3*count,'Failure presentation events not enqueued exactly once'
            failures+=count;decision=state
        elif off==0xdffc and state['active']:
            assert decision and state['clock']==decision['clock']
            due=state['phase']%4==0
            expected={key:decision[key] for key in ('left','right')}
            if due:
                debit=20-(word(decision['speed'])>>4)
                for key,bit in (('left',2),('right',1)):
                    if not decision['damage']&bit:
                        expected[key]=max(80,word(expected[key]-debit))
            assert all(state[key]==value for key,value in expected.items()),(root.name,'cooling',decision,state,expected)
            assert state['coolings']-decision['coolings']==due
            rows.append((state['clock']-epoch,state['phase']%4,int(due)))
            start=None;decision=None
    assert len(rows)>=50 and rows[0][0]==initial-epoch
    assert all(b[0]-a[0]==18 for a,b in zip(rows,rows[1:])), 'Missing logical engine updates'
    data=(root/'final-code.bin').read_bytes()
    blocks=[struct.unpack_from('>4H5I',data,m.start()+8) for m in re.finditer(b'PDENGN01',data)]
    blocks=[row for row in blocks if row[4]]
    assert len(blocks)==1 and blocks[0][-1]==0
    if a.require_failures:
        assert failures>=2,'Need both thermal engine failures'
        assert delivered==[1,2,3]*failures, 'Failure presentations missing, duplicated or out of order'
        assert blocks[0][2]==blocks[0][3]==0 and blocks[0][6]==blocks[0][7], 'Undelivered presentation events'
    cadences.append(rows)
    print(f'{root.name}: {len(rows)} engine decision/cooling updates match native arithmetic; {failures} thermal failures; no event overflow')
length=min(map(len,cadences))
for rows in cadences[1:]:assert rows[:length]==cadences[0][:length], 'Logical engine cadence differs across CPUs'
if len(cadences)>1:print(f'{length} common engine cadence updates match; temperature equality requires matched RNG histories')
