#!/usr/bin/env python3
"""FR0g: parse a blitlog capture, verify a Python reference blitter per blit,
and summarize the frame's blits.

  fr0_blits.py CAPTURE_DIR            -> CAPTURE_DIR/blits.json

Each blit is replayed in isolation from its logged pre-blit channel bytes and
compared with the logged D bytes after it (taken at the next blit start).
Semantics follow the measurement emulator (UAE blitter.cpp dofast/desc/line).
"""
import json, struct, sys, collections
from pathlib import Path

CHIP = 2 << 20


def parse(path):
    data = Path(path).read_bytes(); at = 0; blits = []; u = lambda: struct.unpack_from('<I', data, at)[0]
    while at < len(data):
        magic = u(); at += 4
        if magic == 0x31544c42:
            f = struct.unpack_from('<15I', data, at); at += 60
            idx, pc, con, masks, apt, bpt, cpt, dpt, amod, bmod, cmod, dmod, ab, cd, size = f
            s32 = lambda v: v - (1 << 32) if v & 0x80000000 else v
            b = dict(index=idx, pc=pc, con0=con >> 16, con1=con & 0xffff, afwm=masks >> 16, alwm=masks & 0xffff,
                     apt=apt, bpt=bpt, cpt=cpt, dpt=dpt, amod=s32(amod), bmod=s32(bmod), cmod=s32(cmod), dmod=s32(dmod),
                     adat=ab >> 16, bdat=ab & 0xffff, cdat=cd & 0xffff, h=size >> 16, v=size & 0xffff, regions=[])
            while True:
                kind = u(); at += 4
                if kind == 0:
                    break
                addr, ln = struct.unpack_from('<II', data, at); at += 8
                b['regions'].append((chr(kind), addr, data[at:at + ln])); at += ln
            blits.append(b)
        elif magic == 0x54464144:
            idx = u(); at += 4
            kind, addr, ln = struct.unpack_from('<III', data, at); at += 12
            assert blits[-1]['index'] == idx
            blits[-1]['after'] = (addr, data[at:at + ln]); at += ln
        else:
            raise ValueError(hex(magic))
    return blits


FILL = {}
for d in range(256):
    for i in range(4):
        fc = i & 1; x = d; m = 1
        while m != 0x100:
            t = x
            if fc:
                x = x | m if i & 2 else x ^ m
            if t & m:
                fc ^= 1
            m <<= 1
        FILL[d, i] = (x, fc)


def minterm(mt, a, b, c):
    r = 0
    for i in range(8):
        if mt >> i & 1:
            r |= (a if i & 4 else ~a) & (b if i & 2 else ~b) & (c if i & 1 else ~c)
    return r & 0xffff


def rd(m, a):
    a &= CHIP - 1; return m[a] << 8 | m[a + 1]


def wr(m, a, v):
    a &= CHIP - 1; m[a] = v >> 8 & 255; m[a + 1] = v & 255


def blit(m, b):
    con0, con1 = b['con0'], b['con1']; mt = con0 & 255
    if con1 & 1:
        return line(m, b)
    desc = con1 & 2; fill = con1 & 0x18; ife = 2 if con1 & 8 else 0
    ash = con0 >> 12; bsh = con1 >> 12; h, v = b['h'] or 64, b['v'] or 1024
    use = [con0 & x for x in (0x800, 0x400, 0x200, 0x100)]
    pa, pb, pc, pd = b['apt'], b['bpt'], b['cpt'], b['dpt']
    step = -2 if desc else 2; sgn = -1 if desc else 1
    aold = bold = 0; cdat = b['cdat']; adat = b['adat']
    # B disabled: hold as written to BLTBDAT (pre-shifted by the custom write).
    bhold = ((b['bdat'] << bsh) >> 16 if desc and bsh else b['bdat'] >> bsh) & 0xffff if desc else (b['bdat'] >> bsh) & 0xffff
    for j in range(v):
        fc = 1 if con1 & 4 else 0
        for i in range(h):
            if use[0]:
                adat = rd(m, pa); pa += step
            a = adat
            if i == 0:
                a &= b['afwm']
            if i == h - 1:
                a &= b['alwm']
            ah = ((a << 16 | aold) >> (16 - ash) if desc else (aold << 16 | a) >> ash) & 0xffff
            aold = a
            if use[1]:
                bd = rd(m, pb); pb += step
                bhold = ((bd << 16 | bold) >> (16 - bsh) if desc else (bold << 16 | bd) >> bsh) & 0xffff
                bold = bd
            if use[2]:
                cdat = rd(m, pc); pc += step
            d = minterm(mt, ah, bhold, cdat)
            if fill:
                lo, f1 = FILL[d & 255, ife + fc]; hi, fc = FILL[d >> 8, ife + f1]; d = lo | hi << 8
            if use[3]:
                wr(m, pd, d); pd += step
        if use[0]: pa += sgn * b['amod']
        if use[1]: pb += sgn * b['bmod']
        if use[2]: pc += sgn * b['cmod']
        if use[3]: pd += sgn * b['dmod']


def line(m, b):
    con0, con1 = b['con0'], b['con1']; mt = con0 & 255
    assert b['h'] == 2 and not con0 & 0x400, 'line with B or width != 2'
    ash = con0 >> 12; bsh = con1 >> 12
    apt = b['apt']; cpt = b['cpt']; dpt = b['dpt']; bdat = b['bdat']; cdat = b['cdat']
    rot = lambda x, s: ((x >> s) | (x << (16 - s))) & 0xffff
    blineb = rot(bdat, bsh); onedot = 0; loop = 1
    SIGN, SUD, SUL, AUL, SING = 0x40, 0x10, 8, 4, 2
    s16 = lambda x: (x & 0xffff) - 0x10000 if x & 0x8000 else x & 0xffff
    for n in range(b['v'] or 1024):
        pixel = not (con1 & SING) or not onedot; onedot = 1
        con1 = con1 | SIGN if s16(apt) < 0 else con1 & ~SIGN
        if con0 & 0x800:
            apt += s16(b['bmod']) if con1 & SIGN else s16(b['amod'])
        if con0 & 0x200:
            cdat = rd(m, cpt)
        d = minterm(mt, (b['adat'] & b['afwm']) >> ash, 0xffff if blineb & 1 else 0, cdat)
        ovf = 0

        def incx():
            nonlocal cpt, ovf
            if ash == 15: cpt += 2
            ovf = 1

        def decx():
            nonlocal cpt, ovf
            if ash == 0: cpt -= 2
            ovf = -1
        if not con1 & SIGN and not con1 & SUD:
            decx() if con1 & SUL else incx()
        if con1 & SUD:
            decx() if con1 & AUL else incx()
        ash = (ash + ovf) & 15
        if loop:
            def dy(sign):
                nonlocal cpt, onedot
                if con0 & 0x200:
                    cpt += sign * b['cmod']; onedot = 0
            if not con1 & SIGN and con1 & SUD:
                dy(-1) if con1 & SUL else dy(1)
            if not con1 & SUD:
                dy(-1) if con1 & AUL else dy(1)
            loop = 0
        bsh = (bsh - 1) & 15; blineb = rot(bdat, bsh)
        if pixel and con0 & 0x200:
            wr(m, dpt, d)
        dpt = cpt; loop = 1


def kind(b):
    con0, con1 = b['con0'], b['con1']
    if con1 & 1:
        return 'line'
    ch = ''.join(c for c, bit in zip('ABCD', (0x800, 0x400, 0x200, 0x100)) if con0 & bit)
    return ch + ('-fill' if con1 & 0x18 else '') + ('-desc' if con1 & 2 else '')


def main(p):
    p = Path(p); blits = parse(p / 'blits.bin'); bad = []
    stats = collections.Counter(); words = collections.Counter()
    for b in blits:
        m = bytearray(CHIP + 2)
        for k, addr, data in b['regions']:
            m[addr:addr + len(data)] = data
        blit(m, b)
        k = kind(b); stats[k] += 1; words[k] += (b['h'] or 64) * (b['v'] or 1024) if k != 'line' else (b['v'] or 1024)
        if 'after' in b:
            addr, data = b['after']
            if bytes(m[addr:addr + len(data)]) != data:
                diff = next(i for i in range(len(data)) if m[addr + i] != data[i])
                bad.append({'index': b['index'], 'kind': k, 'first_diff': hex(addr + diff), 'con0': hex(b['con0']),
                            'con1': hex(b['con1']), 'size': [b['h'], b['v']]})
    out = {'blits': len(blits), 'verified': sum(1 for b in blits if 'after' in b) - len(bad), 'mismatches': bad[:40],
           'mismatch_count': len(bad), 'by_kind': dict(stats), 'words_by_kind': dict(words)}
    (p / 'blits.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'mismatches'}, indent=1)); print(bad[:8])
    return blits


if __name__ == '__main__':
    main(sys.argv[1])
