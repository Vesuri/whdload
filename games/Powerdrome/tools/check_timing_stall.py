#!/usr/bin/env python3
"""Verify a single PAL simulation-stall fixture and subsequent elapsed-time accounting.

Run the world/input/resource checks too: this checks stall ownership and recovery,
not full gameplay-state equivalence. A requested 250 ms rounds up to 260 ms on PAL.
"""
import argparse
import json
from pathlib import Path
import re
import struct
from check_timing_capacity import check as check_capacity


def u32(data, offset):
    return struct.unpack_from('>I', data, offset)[0]


def stall_tag(data, frame):
    # Follow the installed timing_frame's first BSR.W and the fixture's LEA.
    # The growing prototype can exceed a fixed tag-search window, and stale
    # loader copies must not be selected by a matching tag alone.
    assert data[frame:frame+8]==bytes.fromhex('40e748e7e0c06100'), 'Missing stall call in live allocator'
    routine=frame+8+struct.unpack_from('>h',data,frame+8)[0]
    assert 0 <= routine < len(data)-4 and data[routine:routine+2]==bytes.fromhex('43fa')
    tag=routine+2+struct.unpack_from('>h',data,routine+2)[0]
    assert 0 <= tag <= len(data)-32 and data[tag:tag+8]==b'PDSTALL1'
    return tag


def check(root):
    config=json.loads((root/'configuration.json').read_text())
    game=int((root/'game-base.txt').read_text(),0)
    base=int((root/'dump-base.txt').read_text(),0)
    chip=(root/'chip.bin').read_bytes()
    frame=u32(chip,game+0xca46)-base
    initial=(root/'code.bin').read_bytes()
    final=(root/'final-code.bin').read_bytes()
    assert 0 <= frame < len(initial)
    tag=stall_tag(initial,frame)
    assert stall_tag(final,frame)==tag, 'Live stall fixture moved'
    before=struct.unpack_from('>6I',initial,tag+8)
    count,start,end,clock,ticks,requested=struct.unpack_from('>6I',final,tag+8)
    assert before[:5]==(0,0,0,0,0) and before[5]==requested, 'Stall already occurred before capture'
    assert count==1 and requested in (100,250,500)
    fields=(requested+19)//20
    assert end-start==fields, 'Stall did not have the specified PAL duration'
    origin=u32(chip,game+0x48fe)
    assert origin<=start<end<=origin+int(config['FIELDS'])
    assert ticks>=200
    rows=[]
    for field,values in re.findall(r'^PDW20_EVENT (-?\d+) 0xcedc (.+)$',
                                 (root/'swaps-gdb.txt').read_text(),re.M):
        rows.append((origin+int(field),int(values.split()[0])))
    assert rows
    assert not any(start<field<end for field,_ in rows), 'World progressed inside the stall'
    resumed=[(field,tick) for field,tick in rows if field>=end]
    assert resumed and resumed[0][1]==clock, 'Resume skipped or repeated a logical world step'
    assert all(b[1]-a[1]==4 for a,b in zip(rows,rows[1:])), 'World clock lost or repeated time'
    # Require eventual service of every 20-ms interval that elapsed by release.
    assert resumed[-1][1]>=end*4, 'Capture ends before the stall elapsed work is serviced'
    check_capacity(root)
    print(f'{root.name}: one {requested} ms requested stall, {fields*20} ms observed; '
          f'world held and resumed at clock {clock}; elapsed work through release serviced')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures',type=Path,nargs='+')
    for capture in parser.parse_args().captures:
        check(capture)
