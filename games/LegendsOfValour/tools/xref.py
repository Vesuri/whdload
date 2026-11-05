#!/usr/bin/env python3
"""xref.py HUNK:OFF[,HUNK:OFF...] [SPAN]: absolute references (relocations) in the decrunched
AMIGA2 to [OFF, OFF+SPAN) of HUNK, as hN:offset of the referencing longword."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import unpack

def relocs(b):
    l = lambda o: struct.unpack_from('>I', b, o)[0]
    o, i, out = 20 + 4 * l(8), 0, []
    hs = unpack.hunks(b)
    while o < len(b):
        t = l(o) & 0x3fffffff
        if t in (0x3e9, 0x3ea): o += 8 + l(o + 4) * 4
        elif t == 0x3eb: o += 8
        elif t == 0x3ec:
            o += 4
            while (c := l(o)):
                for k in range(c):
                    at = l(o + 8 + 4 * k)
                    out.append((i, at, l(o + 4), l(hs[i][1] + at)))
                o += 8 + 4 * c
            o += 4
        elif t == 0x3f2: o += 4; i += 1
        else: break
    return out

if __name__ == '__main__':
    b = open(os.path.join(unpack.ROOT, 'tmp/unpacked/AMIGA2'), 'rb').read()
    span = int(sys.argv[2], 0) if len(sys.argv) > 2 else 2
    rs = relocs(b)
    for t in sys.argv[1].split(','):
        h, off = t.split(':'); h = int(h.lstrip('h')); off = int(off, 16)
        hits = [f'h{i}:{at:05x}' for i, at, th, v in rs if th == h and off <= v < off + span]
        print(f'h{h}:{off:05x}: {len(hits)} refs: ' + ' '.join(hits))
