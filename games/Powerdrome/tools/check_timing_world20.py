#!/usr/bin/env python3
"""Verify 20-ms world steps, rational 90-ms controls, and their retained time debt."""
import argparse
import json
from pathlib import Path
import re
import struct
from coverage_status import fixture
from timing_report import input_state


def block(path, tag, initialized_offset, fmt, offset):
    data=path.read_bytes()
    hits=[m.start() for m in re.finditer(tag,data)
          if struct.unpack_from('>H',data,m.start()+initialized_offset)[0]]
    assert len(hits)==1,(path,tag,len(hits))
    return struct.unpack_from(fmt,data,hits[0]+offset)

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('captures',type=Path,nargs='+')
p.add_argument('--practice',action='store_true',help='Require the bounded CUSTOM5=3 practice route with no opponents')
a=p.parse_args();histories=[]
for root in a.captures:
    initial=block(root/'code.bin',b'PDW20T01',8,'>III',12)
    final=block(root/'final-code.bin',b'PDW20T01',8,'>III',12)
    epoch=fixture(root/'code.bin')['epoch']*4
    control_clock=input_state(root/'code.bin')['clock']
    log=(root/'swaps-gdb.txt').read_text()
    events=[(int(off,16),list(map(int,v.split()))) for off,v in
            re.findall(r'^PDW20_EVENT -?\d+ (0x[0-9a-f]+) (.+)$',log,re.M)]
    finished=[v for off,v in events if off==0xcedc]
    assert len(finished)>=50
    slow=initial[2]
    for i,v in enumerate(finished):
        clock,count,slow_count,due,next_control,fall,impulse,engine=v
        assert clock==initial[0]+4*i and count==initial[1]+1+i, 'Missing or repeated 20-ms world step'
        expected=clock>=control_clock
        assert due==expected, 'Slow update did not follow its rational 90-ms deadline'
        if expected:control_clock+=18;slow+=1
        assert next_control==control_clock and slow_count==slow, 'Slow update count or input deadline diverged'
        assert 0<next_control-clock<=18, 'Historical controls advanced beyond the current world step'
    assert 0<=final[1]-initial[1]-len(finished)<=1
    assert 0<=final[2]-slow<=1
    assert final[0]-initial[0]==4*len(finished), 'World time lost during a completed step'
    input_advance=input_state(root/'final-code.bin')['clock']-input_state(root/'code.bin')['clock']
    assert input_advance%18==0
    pending_controls=final[2]-initial[2]-input_advance//18
    assert 0<=pending_controls<=final[1]-initial[1]-len(finished)<=1
    if pending_controls:
        # A field boundary may stop inside centering/orientation before the
        # started slow update reaches its control completion. Prove that exact
        # endpoint from independent ownership/due/clock state, not a tolerance.
        assert final[2]==slow+1
        assert block(root/'final-code.bin',b'PDW20T01',8,'>H',10)==(1,)
        assert block(root/'final-code.bin',b'PDWORLD1',8,'>H',8)==(1,)
        assert input_state(root/'final-code.bin')['clock']==control_clock
    else:
        assert input_advance==18*(final[2]-initial[2])
    world=[(int(off,16),list(map(int,v.split()))) for off,v in
           re.findall(r'^PDWORLD_EVENT -?\d+ (0x[0-9a-f]+) (.+)$',log,re.M)]
    moved=[v for off,v in world if off==0xcde2]
    ended=[v for off,v in world if off==0xcedc]
    assert len(ended)==len(finished) and all(v[3]==4 for v in moved), 'Movement used a non-20-ms interval'
    assert all(v[3]==(18 if t[3] else 4) for v,t in zip(ended,finished)), 'Wrong opponent or movement interval at world end'
    opponents=[list(map(int,v.split())) for v in re.findall(r'^PDTIME_EVENT -?\d+ 0xd56c (.+)$',log,re.M)]
    if a.practice:
        config=json.loads((root/'configuration.json').read_text())
        assert re.search(r'\bCUSTOM5=3\b',config['WHD_ARGS']) and int(config['FIELDS'])<=500
        game=int((root/'game-base.txt').read_text(),0)
        for name in ('chip.bin','final-chip.bin'):
            data=(root/name).read_bytes()
            assert struct.unpack_from('>H',data,game+0xa6e+0xbe)[0]!=0
            assert struct.unpack_from('>h',data,game+0xa6e+0x340)[0]==-1
        assert not opponents, 'Opponent movement occurred in the opponent-free practice route'
    else:
        assert opponents and all(v[2]==18 for v in opponents), 'Opponent updates escaped the slow cadence'
    # The frame allocator must retain everything it did not assign to world steps.
    old=block(root/'code.bin',b'PDTIME01',8,'>7I',12)
    new=block(root/'final-code.bin',b'PDTIME01',8,'>7I',12)
    # last, phase, native loop, ticks, frames, controls, resources
    assert new[0]-old[0]+old[1]==4*(new[3]-old[3])+new[1], 'Frame allocator discarded elapsed world time'
    outstanding=new[3]-(initial[1]+len(finished))
    assert outstanding>=0
    fall_steps=sum(bool(v[5]) for v in finished);impulse_steps=sum(bool(v[6]) for v in finished)
    histories.append([(v[1]-epoch,*v[3:]) for v in ended])
    print(f'{root.name}: {len(finished)} consecutive 20-ms steps; {slow-initial[2]} slow updates at rational 90-ms deadlines; {len(opponents)} opponent reads at 90 ms')
    print(f'  Retained allocator debt {new[1]*5} ms; assigned unfinished steps {outstanding}; pending started controls {pending_controls}; nonzero fall-age samples {fall_steps}, impulse samples {impulse_steps}')
if len(histories)>1:
    length=min(map(len,histories))
    for root,rows in zip(a.captures[1:],histories[1:]):
        mismatch=next(((i,x,y) for i,(x,y) in enumerate(zip(histories[0][:length],rows[:length])) if x!=y),None)
        assert mismatch is None,(root.name,'20-ms state mismatch (index, reference, actual)',mismatch)
    print(f'{length} common sampled player/engine/RNG states match at identical 20-ms world times')
