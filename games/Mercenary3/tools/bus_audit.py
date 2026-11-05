#!/usr/bin/env python3
"""What does the CPU use the chip bus for? Slot census from kept route traces.

  KEEP_TRACE=1 python3 tools/route_profile.py tmp/prof/bus
  python3 tools/bus_audit.py tmp/prof/bus [FIRST_FIELD]

Every field's DMA records form the full slot grid (227 slots x 313 lines on PAL). CPU records
carry the address, the direction (reg $10xx read, $11xx write), the size (reg bits 0..2) and
whether the access is an instruction fetch (extra 0) or data (extra 1). This splits the CPU's
chip accesses by kind and by memory region, counts misaligned longwords, and compares slot use
inside the bitplane fetch window with the rest of the field. From FIRST_FIELD (default 175:
gameplay). Instruction records give the CPU cycles per field for the cost estimate.
Last, the remaining traffic by place: the VERTB counter poll and display-buffer writes apart,
code fetches per Disk.1 4 KB page and data accesses per named range or 4 KB chip page.
"""
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from amigaxdev.callprofile import DMA_NAMES
from route_profile import IMAGE, IMAGE_END

# The display buffers (4 planes of 8000 bytes each) and the supervisor stack above the second.
REGIONS = ((0x68000, 0x6fd00, 'display buffer'), (0x78000, 0x7fd00, 'display buffer'),
           (0x7fd00, 0x80000, 'stack (top of chip)'), (IMAGE, IMAGE_END, 'game image'),
           (0, IMAGE, 'below the image'))
SLOTS, LINES = 227, 313
# Bitplane fetch lines (DIWSTRT/DIWSTOP $2c81/$f4c1 in the game's copper lists).
WINDOW = range(0x2c, 0xf4)


# Named chip ranges for the per-place breakdown (docs/internals.md: P1 restore set, M2).
PLACES = ((0, 0x340, 'vectors, $C0 calls'), (0x340, 0x4000, 'render scratch'),
          (0x5350, 0x8000, 'game variables'))


def place(kind, a):
    if a in (0x529f4, 0x529f6):
        return 'VERTB counter $529F4 (publication wait)'
    if 0x68000 <= a < 0x80000:
        return 'display buffers, stack'
    if kind == 'fetch' and IMAGE <= a < IMAGE_END:
        return f'code, Disk.1 page ${(a + 0x3cb0) & ~0xfff:05x}'
    for lo, hi, name in PLACES:
        if lo <= a < hi:
            return f'{name} ${lo:05x}..${hi - 1:05x}'
    return 'custom chips' if a >= 0xdff000 else f'chip page ${a & ~0xfff:05x}'


def region(a):
    for lo, hi, name in REGIONS:
        if lo <= a < hi:
            return name
    return 'custom chips' if 0xdff000 <= a < 0xe00000 else f'other {a >> 16:02x}xxxx'


def main():
    d = sys.argv[1]
    first = int(sys.argv[2]) if len(sys.argv) > 2 else 175
    chunks = sorted(f for f in os.listdir(d) if f.startswith('chunk-') and f.endswith('.bin'))
    chunks = [f for f in chunks if int(f[6:11]) >= first]
    kinds = collections.Counter()           # (kind, region) -> accesses
    sizes = collections.Counter()           # (kind, size) -> accesses
    misaligned = collections.Counter()      # kind -> long accesses at an address = 2 mod 4
    slots = {True: collections.Counter(), False: collections.Counter()}  # in window -> type
    places = collections.Counter()          # (kind, place) -> accesses
    nfields = cycles = 0
    for name in chunks:
        t = barto.load(os.path.join(d, name))
        for f in t.fields:
            nfields += 1
            cycles += sum(c for pc, c, _ in t.instructions(f))
            dma, size = f.dma, f.dma_size
            assert len(dma) == size * SLOTS * LINES, (name, f.index, len(dma) // size)
            for i in range(0, len(dma), size):
                typ = dma[i + 29]
                line = i // size // SLOTS
                slots[line in WINDOW][typ] += 1
                if typ != 2:
                    continue
                reg = dma[i] | dma[i + 1] << 8
                addr = int.from_bytes(dma[i + 12:i + 16], 'little')
                kind = 'write' if reg & 0x100 else 'data read' if dma[i + 31] else 'fetch'
                assert not (kind == 'write' and not dma[i + 31]), (name, hex(reg))
                width = 4 if reg & 4 else 2 if reg & 2 else 1
                kinds[(kind, region(addr))] += 1
                places[(kind, place(kind, addr))] += 1
                sizes[(kind, width)] += 1
                if width == 4 and addr & 2:
                    misaligned[kind] += 1
        print(f'{name}: {nfields} fields', file=sys.stderr)
    cpu = sum(kinds.values())
    print(f'Chip-bus CPU accesses, fields {first}.. ({nfields} fields): {cpu / nfields:,.0f} per field; '
          f'CPU cycles {cycles / nfields:,.0f} per field')
    by_kind = collections.Counter()
    for (k, _), n in kinds.items():
        by_kind[k] += n
    for k in ('fetch', 'data read', 'write'):
        print(f'  {k:10} {by_kind[k] / nfields:9,.0f} per field  {100 * by_kind[k] / cpu:5.1f}%   '
              + '  '.join(f'{w * 8}-bit {100 * sizes[(k, w)] / max(by_kind[k], 1):.0f}%' for w in (1, 2, 4)))
    print('By region:')
    for (k, r), n in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f'  {k:10} {r:22} {n / nfields:9,.0f} per field  {100 * n / cpu:5.1f}%')
    print('Longword accesses at an address = 2 mod 4: '
          + ', '.join(f'{k} {misaligned[k] / nfields:,.0f}' for k in ('fetch', 'data read', 'write')))
    print(f'Slot use inside the bitplane lines ${WINDOW.start:02x}..${WINDOW.stop - 1:02x} and outside:')
    for inside in (True, False):
        n = sum(slots[inside].values())
        print(f'  {"inside " if inside else "outside"} '
              + '  '.join(f'{DMA_NAMES.get(k, k)} {100 * v / n:.1f}%' for k, v in sorted(slots[inside].items())))

    print('By place (top 30):')
    for (k, p), n in places.most_common(30):
        print(f'  {k:10} {p:42} {n / nfields:9,.0f} per field')


if __name__ == '__main__':
    main()
