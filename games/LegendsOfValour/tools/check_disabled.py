#!/usr/bin/env python3
"""Check optional patch bytes against the local original, allowing hunk relocations.
No game bytes are emitted. Use SLAVE=capture/slave.slave when checking a VERIFY capture.
"""
import argparse
import re
import struct
from pathlib import Path
from lov_report import regions
from unpack import hunks

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--custom2', type=lambda x: int(x, 0), default=0,
               help='enabled option mask; check only disabled patches (default all off)')
p.add_argument('--display-timing', action='store_true',
               help='also require original frame-cap, display clock call and beam-wait code')
p.add_argument('--base', type=lambda x: int(x, 0), default=0xc00000)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
original = (root/'tmp/unpacked/AMIGA2').read_bytes()
layout = hunks(original)
# Parse RELOC32 blocks separately; unpack.hunks exposes memory flags, not relocations.
relocations = [[] for _ in layout]
cursor = 20+4*len(layout)
hunk = 0
def long(at):
    return struct.unpack_from('>I', original, at)[0]
while hunk < len(layout):
    kind = long(cursor) & 0x3fffffff
    cursor += 4
    if kind in (0x3e9,0x3ea):
        cursor += 4+4*long(cursor)
    elif kind == 0x3eb:
        cursor += 4
    elif kind == 0x3ec:
        while long(cursor):
            count, target = long(cursor), long(cursor+4)
            cursor += 8
            offsets = [long(cursor+4*i) for i in range(count)]
            relocations[hunk].append((target, offsets))
            cursor += count*4
        cursor += 4
    elif kind == 0x3f2:
        hunk += 1
    else:
        raise ValueError(f'unsupported hunk type {kind:#x}')
mem = (a.capture/'code.bin').read_bytes()
r = {n: lo for lo, hi, n, origin in regions(mem, a.base)}
# Every optional mutation has a PERF_RANGE declaration beside its patch installer.
ranges = []
for source in (root/'whdload').glob('*.s'):
    ranges += [(int(h), int(o,16), int(n), int(bit or 0)) for h,o,n,bit in
               re.findall(r'PERF_RANGE h(\d+):([0-9a-fA-F]+) (\d+)(?: bit=(\d+))?', source.read_text())]
ranges = [entry for entry in ranges if not a.custom2 & (1 << entry[3])]
optional_count = len(ranges)
if a.display_timing:
    ranges += [(12,0x5e2a,0x50,None), (12,0x5ea6,12,None), (12,0x63ce,0x22,None)]
assert ranges, "no disabled patch ranges selected"
for h, offset, size, bit in ranges:
    _, file_offset, file_size, alloc, flags = layout[h]
    expected = bytearray(original[file_offset:file_offset+file_size])
    for target, offsets in relocations[h]:
        for at in offsets:
            value = struct.unpack_from('>I', expected, at)[0]
            struct.pack_into('>I', expected, at, (value+r[f'h{target}']) & 0xffffffff)
    at = r[f'h{h}']-a.base+offset
    assert mem[at:at+size] == expected[offset:offset+size], f'optional patch active at h{h}:{offset:05x}'
print(f'CUSTOM2={a.custom2}: {optional_count} declared optional ranges retain original instructions')
if a.display_timing:
    print('Original display frame-cap, clock call and beam-wait instructions are intact')
