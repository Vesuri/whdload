#!/usr/bin/env python3
"""Verify runtime results from the private 68k deadline-transfer vectors.

These execute the actual helper, but do not prove pit/resume integration or
wraparound beyond the native nonnegative clock/deadline domain.
"""
import argparse
from pathlib import Path
import struct
from weather_cycle_state import locate

CASES=(
    (0xffffffff,1000,200,0xffffffff),
    (0x80000000,1000,200,0x80000000),
    (1500,1000,200,700),
    (1000,1000,200,200),
    (999,1000,200,200),
    (1,10000,200,200),
    (0,10,0,0),
    (1,0,0,1),
    (0x7fffffff,0x7ffffffe,100,101),
    (0x7fffffff,0x7fffffff,100,100),
    (0x7ffffffe,0x7fffffff,100,100),
)


def validate_record(code,tag,base):
    assert struct.unpack_from('>3I',code,tag+8)==(1,len(CASES),0), 'Fixture incomplete or reported mismatches'
    for index,expected in enumerate(CASES):
        pos=tag+20+32*index
        values=struct.unpack_from('>8I',code,pos)
        assert values[:4]==expected, 'Unexpected fixture input/expected-result table'
        assert values[4]==expected[3], f'Wrong transferred deadline in case {index}'
        assert values[5:7]==expected[1:3], 'Clock input registers changed'
        assert values[7]==base+pos+16, 'Destination pointer changed'
    return [case[3] for case in CASES]


def check(root):
    base=int((root/'dump-base.txt').read_text(),0)
    game=int((root/'game-base.txt').read_text(),0)
    results=[]
    for prefix in ('','final-'):
        chip=(root/(prefix+'chip.bin')).read_bytes()
        code=(root/(prefix+'code.bin')).read_bytes()
        address=locate(chip,code,game,base)
        assert address is not None
        tag=code.find(b'PDWTFR01',address-base+72,address-base+4096)
        assert tag>=0 and code.find(b'PDWTFR01',tag+1,address-base+4096)<0
        results.append(validate_record(code,tag,base))
    assert results[0]==results[1]
    print(f'{root.name}: all {len(CASES)} assembled transfer cases pass in both snapshots; clocks/destination preserved')
    return results[0]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures',type=Path,nargs='+')
    results=[check(root) for root in p.parse_args().captures]
    assert all(r==results[0] for r in results), 'Transfer results differ'
    print('Sentinel/future/due/overdue/near-boundary arithmetic verified; lifecycle integration remains separate.')
