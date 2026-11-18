#!/usr/bin/env python3
"""The CPU's chip-bus accesses in a trace, by what they reach.

    python3 tools/archipelagos.py profile N "" FILE     (a stopped server, in play)
    python3 tools/cpuchip.py FILE

Counts the trace's DMA slot records of the CPU (each a chip-bus access: 0x10nn reads and
0x11nn writes of nn bytes) by target, a field on average. Code fetches are the reads of
the program image within 10 bytes after an instruction the trace executed; the two wait
loops' reads (the field counter at $1487E, offset $12862, and DMACONR) are listed apart.
Only the screen buffers have to be in chip memory for the CPU's sake; everything else
here could be in fast memory. With the body in fast memory (a 68020+ with ExpMem) the
program image here is the chip copy: its accesses are split by the slave's chip blocks
(CHIP627 in src/ArchipelagosFiles_WHD.s); one outside them would be a reference the
relocation missed.
"""
import collections
import os
import re
import struct
import sys

sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
from amigaxdev import barto  # noqa: E402

BODY, END = 0x201c, 0x16314
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def chip_blocks():
    src = open(os.path.join(ROOT, 'src/ArchipelagosFiles_WHD.s'), encoding='latin-1').read()
    m = re.search(r'^CHIP627\s+dc\.l\s+(.*?)-1', src, re.S | re.M)
    v = [int(x, 16) for x in re.findall(r'\$([0-9a-f]+)', m.group(1))]
    return list(zip(v[::2], v[1::2]))


BLOCKS = chip_blocks()


def region(a, code):
    if 0x700 <= a < 0x800:
        return 'stack ($700-$800)'
    if 0x5c780 <= a < 0x70000:
        return 'screen buffers ($5C780-$6FFFF)'
    if 0x70000 <= a < 0x80000:
        return 'map ($70000-$7FFFF)'
    if a in (0x1487e, 0x14880):
        return 'VBL wait loop (field counter)'
    if a == 0xdff002:
        return 'blitter wait loop (DMACONR)'
    if 0xdff000 <= a < 0xe00000:
        return 'other custom registers'
    if BODY <= a < END:
        if a in code:
            return 'program image: code fetch'
        o = a - BODY
        if any(lo <= o < hi for lo, hi in BLOCKS):
            return 'program image: data, in a chip block'
        return 'program image: data, outside the chip blocks'
    return 'other chip'


def main(path):
    t = barto.load(path)
    code = set()
    for f in t.fields:
        for pc, _, _ in t.instructions(f):
            if pc is not None and BODY <= pc < END:
                code.update(range(pc, pc + 10))
    nf = len(t.fields)
    count = collections.Counter()
    for f in t.fields:
        d = bytes(f.dma)
        for i in range(0, len(d), f.dma_size):
            if d[i + 29] != 2:
                continue
            kind = struct.unpack_from('<H', d, i)[0]
            addr = struct.unpack_from('<I', d, i + 12)[0]
            count[(region(addr, code), 'write' if kind & 0x100 else 'read')] += 1
    tot = sum(count.values())
    spin = sum(v for (r, _), v in count.items() if 'wait loop' in r)
    print(f'{nf} fields: {tot / nf:.0f} CPU chip accesses a field, '
          f'{(tot - spin) / nf:.0f} outside the wait loops')
    for (r, rw), v in sorted(count.items(), key=lambda x: -x[1]):
        share = '' if 'wait loop' in r else f'  {100 * v / (tot - spin):5.1f}% of those'
        print(f'  {r:34} {rw:5} {v / nf:7.0f}{share}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
