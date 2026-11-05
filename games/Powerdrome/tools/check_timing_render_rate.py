#!/usr/bin/env python3
"""Check aggregate PAL render-pacing accounting, not release throughput or per-frame state.

Use world/control/resource comparisons separately. Actual completed presentations are
reported by frames.txt; fixture release rate is not itself a presentation-rate measurement.
"""
import argparse
from collections import Counter
import re
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


def presentation_intervals(root, origin, lastwall):
    log=(root/'swaps-gdb.txt').read_text()
    # Infer alignment from independently observed guest VBL values, not from
    # the initial snapshot: the debugger starts counting at an IRQ boundary.
    clocks=re.findall(r'^PDINITIAL_EVENT (-?\d+) 0x[0-9a-f]+ (.+)$',log,re.M)
    offsets={int(values.split()[1])-int(field) for field,values in clocks}
    assert len(offsets)==1, 'Guest/debugger field alignment is missing or changed'
    offset=offsets.pop()
    markers=[int(field)+offset for field in re.findall(r'^PDFRAME (-?\d+)$',log,re.M)]
    # Exclude the origin field: a marker there may precede first fixture entry.
    markers=[field for field in markers if origin<field<=lastwall]
    assert len(markers)>=10 and markers[-1]>markers[0], 'Insufficient paced presentation observations'
    gaps=[b-a for a,b in zip(markers,markers[1:])]
    assert all(gap>=0 for gap in gaps), 'Presentation markers went backward'
    counts=Counter(gap*20 for gap in gaps)
    rate=len(gaps)*50/(markers[-1]-markers[0])
    print(f'  Paced-region driving presentation markers: {len(gaps)} intervals, '
          f'{rate:.3f}/s over {(markers[-1]-markers[0])*20} ms; '
          f'interval_ms/count={dict(sorted(counts.items()))}')
    print('  Marker intervals have 20-ms PAL resolution; they do not establish distinct displayed images or release throughput.')
    return markers,counts


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
    presentation_intervals(root,origin,lastwall)
    print('  Pacing and presentation timing only; exact gameplay comparisons remain separate.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures',type=Path,nargs='+')
    for root in p.parse_args().captures:
        check(root)
