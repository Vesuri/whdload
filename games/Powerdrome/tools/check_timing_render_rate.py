#!/usr/bin/env python3
"""Check aggregate PAL render-pacing accounting, not release throughput or per-frame state.

Use world/control/resource comparisons separately. Actual completed presentations are
reported by frames.txt; fixture release rate is not itself a presentation-rate measurement.
"""
import argparse
from pathlib import Path
import struct
from check_timing_capacity import check as check_capacity


def record(data,frame):
    assert data[frame:frame+2] in (bytes.fromhex('40e7'),bytes.fromhex('42e7'))
    assert data[frame+2:frame+8]==bytes.fromhex('48e7e0c06100')
    routine=frame+8+struct.unpack_from('>h',data,frame+8)[0]
    assert 0<=routine<len(data)-4 and data[routine:routine+2]==bytes.fromhex('43fa')
    tag=routine+2+struct.unpack_from('>h',data,routine+2)[0]
    assert 0<=tag<=len(data)-60 and data[tag:tag+8]==b'PDRATE01'
    return struct.unpack_from('>13I',data,tag+8)


def check(root):
    game=int((root/'game-base.txt').read_text(),0)
    base=int((root/'dump-base.txt').read_text(),0)
    chip=(root/'chip.bin').read_bytes()
    frame=struct.unpack_from('>I',chip,game+0xca46)[0]-base
    before=record((root/'code.bin').read_bytes(),frame)
    after=record((root/'final-code.bin').read_bytes(),frame)
    active,hz,origin,count,arrival,deadline,release,phase,waited,late,maxlate,sumlate,pending=after
    assert hz in (10,15,25,50) and before==(0,hz,*([0]*11))
    assert active==1 and count>=10 and pending in (0,1)
    firstwall=struct.unpack_from('>I',chip,game+0x48fe)[0]
    lastwall=struct.unpack_from('>I',(root/'final-chip.bin').read_bytes(),game+0x48fe)[0]
    assert firstwall<=origin<release<=lastwall and origin<=arrival<=lastwall
    periods=count-1
    nominal=(periods*50+hz-1)//hz
    assert release-origin==nominal+sumlate, 'Unaccounted pacing time'
    assert phase==(hz-1+(periods+pending)*50)%hz, 'Incorrect rational pacing phase'
    assert 0<=late<=periods and 0<=maxlate<=sumlate and waited<=release-origin
    assert (late==0)==(sumlate==0)==(maxlate==0)
    if pending:
        nextperiod=((periods+1)*50+hz-1)//hz-nominal
        assert deadline==release+nextperiod and arrival>=release
        assert lastwall<=deadline, 'Unexplained unfinished pacing deadline'
    else:
        assert arrival<=release and deadline<=release
    check_capacity(root)
    measured=periods*50/(release-origin)
    print(f'{root.name}: {hz} Hz requested; {count} allocator releases, {measured:.3f}/s; '
          f'{late} late deadlines, max {maxlate*20} ms, total {sumlate*20} ms; '
          f'{waited*20} ms pacing wait; pending={pending}')
    print('  Aggregate pacing proof only. Inspect completed-frame measurements and exact gameplay comparisons separately.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures',type=Path,nargs='+')
    for root in p.parse_args().captures:
        check(root)
