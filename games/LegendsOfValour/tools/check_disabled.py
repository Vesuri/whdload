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
    ranges += [(int(h), int(o,16), int(n)) for h,o,n in
               re.findall(r'PERF_RANGE h(\d+):([0-9a-fA-F]+) (\d+)', source.read_text())]
for h, offset, size in ranges:
    _, file_offset, file_size, alloc, flags = layout[h]
    expected = bytearray(original[file_offset:file_offset+file_size])
    for target, offsets in relocations[h]:
        for at in offsets:
            value = struct.unpack_from('>I', expected, at)[0]
            struct.pack_into('>I', expected, at, (value+r[f'h{target}']) & 0xffffffff)
    at = r[f'h{h}']-a.base+offset
    assert mem[at:at+size] == expected[offset:offset+size], f'optional patch active at h{h}:{offset:05x}'
print(f'CUSTOM2=0: {len(ranges)} declared optional ranges retain original instructions')
