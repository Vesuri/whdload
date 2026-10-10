#!/usr/bin/env python3
"""Validate every ray-table byte produced by the guest 68000 generator."""
import argparse
import re
import struct
from pathlib import Path
from turning_tables import VIEWS, row

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--base', type=lambda x: int(x, 0), default=0x200000)
p.add_argument('--native-buttons-only', action='store_true',
               help='check the native UI dispatcher without requiring a ray-table dump')
p.add_argument('--fallback', action='store_true')
p.add_argument('--require-all-views', action='store_true')
p.add_argument('--require-wall-twins', action='store_true')
p.add_argument('--require-lifecycle', action='store_true')
p.add_argument('--require-ray-sweeps', action='store_true')
a = p.parse_args()
mem = (a.capture/'code.bin').read_bytes()
chip = (a.capture/'chip.bin').read_bytes() if (a.capture/'chip.bin').exists() else b''
listing = (a.capture/'slave.lst').read_text(errors='replace')
anchor = (a.capture/'anchor.txt').read_text()
slave = int(re.search(r'^slave (0x[0-9a-f]+)', anchor, re.M)[1], 16)

def symbol(name):
    return slave + int(re.search(r'^'+name+r'\s+00:([0-9A-F]{8})\s*$', listing, re.M)[1], 16)

def word(address):
    return struct.unpack_from('>H', mem, address-a.base)[0]

def long(address):
    return struct.unpack_from('>I', mem, address-a.base)[0]

# Precision must not intercept the native UI command dispatcher.
h1 = long(symbol('_hunks') + 4)
h5 = long(symbol('_hunks') + 5*4)
assert word(h1+0x2c00) == 0x4ef9 and long(h1+0x2c02) == h5+0x1a74, \
    'UI button dispatcher no longer calls the native handler'
print('UI command dispatcher retains its native target')
if a.native_buttons_only:
    raise SystemExit(0)

owned, active = long(symbol('_turn_owned')), long(symbol('_turn_active'))
h11 = long(symbol('_h11'))
h12 = long(symbol('_h12'))
if a.fallback:
    assert active == 0 and word(h11+0x6010) == 5 and word(h12+0x38) == 5
    print('Five-degree fallback: no active replacement table; both angle units are five')
else:
    assert owned and owned == active
    table_mem, table_base = (mem, a.base) if active >= a.base else (chip, 0)
    assert table_base <= active and active+144000 <= table_base+len(table_mem), 'table outside capture memory'
    width = word(h11+0x8ca)
    assert width == word(symbol('_turn_width'))
    assert word(h11+0x6010) == word(h12+0x38) == 1
    focal, filename = next((f,n) for w,f,n in VIEWS if w == width)
    original = Path('tmp/game/LegendsOfValour/data',filename).read_bytes()
    stride = 4*(width+8)
    assert stride == word(h12+0x3a)
    for heading in range(180):
        actual = table_mem[active-table_base+heading*stride:active-table_base+(heading+1)*stride]
        if heading % 5 == 0:
            expected = original[heading//5*stride:(heading//5+1)*stride]
        else:
            values = row(width, focal, heading, fixed=True)
            expected = struct.pack('>'+str(len(values))+'H',*values).ljust(stride,b'\0')
        if actual != expected:
            i = next(i for i,(x,y) in enumerate(zip(actual,expected)) if x!=y)
            raise AssertionError(f'width={width}, heading={heading}, byte={i}: {actual[i]:02x} != {expected[i]:02x}')
    print(f'All 180 guest rows exact against the host model, width={width}, '
          f'generations={long(symbol("_turn_generations"))}; both angle units are one')

if a.require_all_views:
    counts = [long(symbol('_turn_verified_views')+4*i) for i in range(3)]
    assert all(counts), f'missing view verification: {counts}'
    print(f'Guest oracle passes for small/medium/large: {counts}')

if a.require_wall_twins:
    counts = [long(symbol('_turn_pixel_counts')+4*i) for i in range(3)]
    assert all(counts), f'missing full wall-rendering twins: {counts}'
    print(f'Legacy-heading wall pixel twins, small/medium/large: {counts}')

if a.require_lifecycle:
    assert long(symbol('_turn_lifecycle_cycles')) == 1
    print('Owned table allocation/free/reallocation cycle completed')

if a.require_ray_sweeps:
    counts = [long(symbol('_turn_sweep_counts')+4*i) for i in range(3)]
    assert counts == [360,360,360], f'incomplete ray sweeps: {counts}'
    print('All 360 headings passed the native ray walker in each of the three views')

if re.search(r'^_turn_generation_fields\s+00:', listing, re.M):
    fields = [long(symbol('_turn_generation_fields')+4*i) for i in range(3)]
    print(f'Last table-generation fields small/medium/large: {fields} (20 ms/field; oracle excluded)')
