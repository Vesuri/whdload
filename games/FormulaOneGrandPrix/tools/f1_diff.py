#!/usr/bin/env python3
"""F1: changed ranges between two f1gp files, as hunk offsets.

  python3 tools/f1_diff.py A B [GAP]    ranges closer than GAP bytes (default 8) merge
"""
import struct, sys


def hunks(f):
    """[(hunk, file offset of its data, size)] of an AmigaDOS load file."""
    o = 4
    assert struct.unpack_from('>I', f, 0)[0] == 0x3f3
    while struct.unpack_from('>I', f, o)[0]:
        o += 4 + 4*struct.unpack_from('>I', f, o)[0]
    o += 4
    n, first, last = struct.unpack_from('>III', f, o)
    o += 12 + 4*(last-first+1)
    out, h = [], 0
    while o < len(f):
        t = struct.unpack_from('>I', f, o)[0] & 0x3fffffff
        if t in (0x3e9, 0x3ea):
            size = 4*struct.unpack_from('>I', f, o+4)[0]
            out.append((h, o+8, size))
            o += 8 + size
        elif t == 0x3eb:
            o += 8
        elif t == 0x3ec:
            o += 4
            while True:
                k = struct.unpack_from('>I', f, o)[0]
                o += 4
                if not k:
                    break
                o += 4 + 4*k
        elif t == 0x3f2:
            h += 1
            o += 4
        else:
            raise ValueError(f'hunk type {t:#x}')
    return out


def relocs(f):
    """{(hunk, offset): target hunk} of every 32-bit relocation."""
    o = 4
    while struct.unpack_from('>I', f, o)[0]:
        o += 4 + 4*struct.unpack_from('>I', f, o)[0]
    o += 4
    n, first, last = struct.unpack_from('>III', f, o)
    o += 12 + 4*(last-first+1)
    out, h = {}, 0
    while o < len(f):
        t = struct.unpack_from('>I', f, o)[0] & 0x3fffffff
        if t in (0x3e9, 0x3ea):
            o += 8 + 4*struct.unpack_from('>I', f, o+4)[0]
        elif t == 0x3eb:
            o += 8
        elif t == 0x3ec:
            o += 4
            while True:
                k = struct.unpack_from('>I', f, o)[0]
                o += 4
                if not k:
                    break
                target = struct.unpack_from('>I', f, o)[0]
                for j in range(k):
                    out[(h, struct.unpack_from('>I', f, o+4+4*j)[0])] = target
                o += 4 + 4*k
        elif t == 0x3f2:
            h += 1
            o += 4
    return out


def where(layout, i):
    for h, s, n in layout:
        if s <= i < s+n:
            return h, i-s
    return None, i


def label(layout, i):
    h, o = where(layout, i)
    return f'h{h}+${o:X}' if h is not None else f'file ${o:X}'


def ranges(a, b, gap=8):
    runs = []
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            if runs and i - runs[-1][1] <= gap:
                runs[-1][1] = i
            else:
                runs.append([i, i])
    return runs


def main():
    a, b = (open(p, 'rb').read() for p in sys.argv[1:3])
    layout = hunks(a)
    runs = ranges(a, b, int(sys.argv[3]) if len(sys.argv) > 3 else 8)
    for s, e in runs:
        print(f'{label(layout, s):>12}  {e-s+1:5}  {a[s:e+1][:12].hex()} -> {b[s:e+1][:12].hex()}')
    print(sum(a[s] != b[s] for s in range(min(len(a), len(b)))), 'bytes in', len(runs),
          'ranges; sizes', len(a), len(b))


if __name__ == '__main__':
    main()
