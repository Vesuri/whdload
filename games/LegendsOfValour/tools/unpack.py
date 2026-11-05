#!/usr/bin/env python3
"""Decrunch a PowerPacker-stub executable (AMIGA2, charact) into the hunk file it carries.

  python3 tools/unpack.py [IN [OUT]]      default tmp/game/LegendsOfValour/data/AMIGA2 -> tmp/unpacked/AMIGA2

The installed AMIGA2 is a two-hunk file: hunk 0 is a 548-byte stub, hunk 1 holds PowerPacker
data (efficiency table 9,10,12,12).  At run time the stub decrunches hunk 1 in place, then acts
as its own LoadSeg: it AllocMems each hunk of the decrunched hunk file, copies and relocates
it, frees its own data hunk and returns into the first new hunk.  This is a port of the stub's
decruncher (AMIGA2 hunk 0 +$17c), so the output is byte-exact with what the stub produces.
`hunks(path)` parses the result (or any hunk file) into [(type, file_offset, size, alloc)].
"""
import os, struct, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'tmp/game/LegendsOfValour/data/AMIGA2')
OUT = os.path.join(ROOT, 'tmp/unpacked/AMIGA2')


def decrunch(packed, table=(9, 10, 12, 12)):
    """packed: hunk 1 data up to its end (the stub starts reading at the last longword)."""
    src = len(packed)
    def rlong():
        nonlocal src
        src -= 4
        return struct.unpack_from('>I', packed, src)[0]
    last = rlong()
    out_len = last >> 8
    out = bytearray(out_len)
    buf, nbits = rlong(), 32  # bit buffer, consumed LSB first
    def bit():
        nonlocal buf, nbits
        if nbits == 0:
            buf, nbits = rlong(), 32
        b = buf & 1
        buf >>= 1; nbits -= 1
        return b
    def bits(n):
        v = 0
        for _ in range(n):
            v = (v << 1) | bit()
        return v
    for _ in range(last & 0xff):  # skip bits
        bit()
    dst = out_len
    while True:
        if not bit():  # literal run, then always a match
            n = 0
            while True:
                x = bits(2); n += x
                if x != 3: break
            for _ in range(n + 1):
                dst -= 1; out[dst] = bits(8)
            if dst <= 0:
                break
        idx = bits(2)
        nb = table[idx]
        if idx == 3:
            off = bits(nb if bit() else 7)
            n = idx
            while True:
                x = bits(3); n += x
                if x != 7: break
        else:
            off = bits(nb)
            n = idx
        for _ in range(n + 2):
            dst -= 1; out[dst] = out[dst + 1 + off]
        if dst <= 0:
            break
    assert dst == 0, dst
    return bytes(out)


def hunks(path_or_bytes):
    b = path_or_bytes if isinstance(path_or_bytes, bytes) else open(path_or_bytes, 'rb').read()
    l = lambda o: struct.unpack_from('>I', b, o)[0]
    assert l(0) == 0x3f3 and l(4) == 0
    n, first, last = l(8), l(12), l(16)
    allocs = [l(20 + 4 * i) & 0x3fffffff for i in range(n)]
    o, out = 20 + 4 * n, []
    i = 0
    while o < len(b) and i < n:
        t = l(o) & 0x3fffffff
        if t in (0x3e9, 0x3ea):
            size = l(o + 4) * 4
            out.append(({0x3e9: 'code', 0x3ea: 'data'}[t], o + 8, size, allocs[i] * 4, l(20 + 4 * i) >> 30))
            o += 8 + size
        elif t == 0x3eb:
            out.append(('bss', None, 0, l(o + 4) * 4, l(20 + 4 * i) >> 30)); o += 8
        elif t == 0x3ec:
            o += 4
            while l(o):
                o += 8 + 4 * l(o)
            o += 4
        elif t == 0x3f2:
            o += 4; i += 1
        else:
            raise ValueError(f'hunk type {t:#x} at {o:#x}')
    return out


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else SRC
    dst = sys.argv[2] if len(sys.argv) > 2 else OUT
    h = hunks(src)
    assert len(h) == 2, h
    _, off, size, _, _ = h[1]
    f = open(src, 'rb').read()
    # The stub starts at hunk 1 + $1713c in AMIGA2: the end of hunk 1's file-backed data.
    packed = f[off:off + size]
    out = decrunch(packed)
    i = out.find(b'\0\0\x03\xf3')
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, 'wb').write(out[i:])
    print(f'{src}: {len(out)} bytes decrunched, hunk file at +{i:#x} -> {dst}')
    for k, (t, o, s, a, mem) in enumerate(hunks(out[i:])):
        print(f'  hunk {k}: {t:4s} file {o if o is None else hex(o)} size {s:#x} alloc {a:#x}'
              + (' CHIP' if mem == 1 else ' FAST' if mem == 2 else ''))


if __name__ == '__main__':
    main()
