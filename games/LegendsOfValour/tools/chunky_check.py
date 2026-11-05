#!/usr/bin/env python3
"""Validate W2 ownership, allocation type and VERIFY lifecycle evidence in a capture."""
import argparse, os, re, struct
from pathlib import Path
from lov_report import regions
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--base', type=lambda x: int(x, 0), default=0xc00000)
p.add_argument('--expect', choices=('auto','public','fast','chip','pool'), default='auto')
p.add_argument('--cycle', action='store_true')
a = p.parse_args(); os.environ['SLAVE'] = str(a.capture/'slave.slave')
b = (a.capture/'code.bin').read_bytes()
lst = (a.capture/'slave.lst').read_text(errors='replace')
r = {n: lo for lo,hi,n,o in regions(b,a.base)}
def number(address):
    return struct.unpack_from('>I',b,address-a.base)[0]
def symbol(n):
    m = re.search(r'^'+n+r'\s+00:([0-9A-F]{8})\s*$',lst,re.M)
    assert m, f'missing {n}'
    return number(r['slave']+int(m[1],16))
ptr = number(r['h11']+0x5fc2)
owned = symbol('_w2_owned'); flags = symbol('_w2_memflags')
if owned: assert flags&1, 'owned allocation is not PUBLIC memory'
print(f'chunky storage: {"captured expansion RAM" if a.base <= ptr < a.base+len(b) else "outside expansion dump (chip on these fixtures)"}')
print('Exec memory flags:',hex(flags))
if a.expect in ('auto','public'):
    if owned:
        assert owned==ptr and flags&1, 'game pointer differs from the owned PUBLIC allocation'
        print('allocation path: Exec PUBLIC')
    else:
        assert a.expect=='auto', 'expected an owned PUBLIC allocation'
        print('allocation path: original pool fallback')
elif a.expect=='fast':
    assert owned==ptr and owned and flags&4 and not flags&2, 'buffer is not the owned FAST allocation'
    assert a.base<=ptr and ptr+20000<=a.base+len(b),'allocation outside captured expansion RAM'
elif a.expect=='chip':
    assert owned==ptr and owned and flags&2 and not flags&4, 'buffer is not the owned CHIP allocation'
else:
    assert owned==0, 'expected original pool allocation'
if a.cycle:
    assert symbol('_w2_cycles')==1,'allocation/free/reallocation cycle did not complete'
    print('allocation/free/reallocation cycle: PASS')
print('W2 ownership/type: PASS')
