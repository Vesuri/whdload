#!/usr/bin/env python3
"""tools/dmaregions.py TRACE [N]: the CPU's chip memory accesses in a Barto trace (FS-UAE
`monitor profile`, a 68000 without caches: every access is in the DMA records), split into
instruction fetches, data reads and writes, and the reads and writes by 4 KB block (the two
screens, $1FAC6-$2F4C5, as one). N (default 22) blocks of each. The data accesses that are
not to the screens or the custom chips are what fast memory can take."""
import collections
import struct
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
import game_server  # noqa: F401,E402  (puts amigaxdev on the path)
import amigaxdev.barto as barto  # noqa: E402

CPU = 2           # DMARECORD_CPU, the record's byte 29
SCREENS = (0x1FAC6, 0x2F4C6)


def region(a):
    return 'screens' if SCREENS[0] <= a < SCREENS[1] else '%05X' % (a & ~0xFFF)


def main(argv):
    t = barto.load(argv[0])
    top = int(argv[1]) if argv[1:] else 22
    reads, writes = collections.Counter(), collections.Counter()
    code = total = 0
    for f in t.fields:
        d, n = bytes(f.dma), f.dma_size
        for i in range(0, len(d), n):
            if d[i + 29] != CPU:
                continue
            total += 1
            reg = d[i] | d[i + 1] << 8          # 0x10xx read, 0x11xx write
            addr = struct.unpack_from('<I', d, i + 12)[0]
            if reg & 0x100:
                writes[region(addr)] += 1
            elif d[i + 31] == 0:                # 0: an instruction fetch, 1: data
                code += 1
            else:
                reads[region(addr)] += 1
    print(f'{len(t.fields)} fields, CPU accesses {total}: instruction fetches {code}, data reads '
          f'{sum(reads.values())}, writes {sum(writes.values())}')
    for name, c in (('reads', reads), ('writes', writes)):
        print(f'{name}:')
        for k, v in c.most_common(top):
            print(f'  {k:8} {v:8} {100 * v / total:5.1f}%')


if __name__ == '__main__':
    main(sys.argv[1:])
