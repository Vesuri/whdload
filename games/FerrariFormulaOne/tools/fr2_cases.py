#!/usr/bin/env python3
"""FR2 oracle cases (FASTRAM_PLAN.md FR2).

  fr2_cases.py [OUT_DIR]      default tmp/build/fr2-data -> FR2Cases.bin, cases.json

Each case is an 80-byte record: an FRB register image ($3c bytes, pointers as
offsets into the oracle scratch) followed by
  $3c size2.w   second BLTSIZE with no other register written (0 = none)
  $3e reloc.w   pointers to rebase: bit 0 A, 1 B, 2 C, 3 D
  $40 seed.l    xorshift32 seed for the scratch contents
  $44 len.l     scratch bytes filled and compared (segments plus guards)
  $48 pattern.w 0 random, 1 sparse (1/8), 2 dense (7/8), 3 very sparse (1/32)
  $4a kind.w    0 FR1 capture, 1 generated
Every case fits the Chip scratch (one display bank, 30,960 bytes, minus the
primer word at the end). The footprint comes from the reference model.
"""
import json, math, random, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fr2_model import Blitter, Mem
from fr0_blits import parse

R = Path(__file__).resolve().parents[1]
CHIP_LIMIT = 30960 - 64
GUARD = 64
REC = 0x50
SCENES = ['normal', 'solo', 'grid', 'dense', 'start', 'pit1', 'pit2']
FRB = dict(con0=0x00, con1=0x02, afwm=0x04, alwm=0x06, cpt=0x08, bpt=0x0c, apt=0x10, dpt=0x14, size=0x18,
           cmod=0x20, bmod=0x22, amod=0x24, dmod=0x26, cdat=0x30, bdat=0x32, adat=0x34)


def xorshift_fill(n, seed, pattern):
    x = seed & 0xffffffff or 1
    out = bytearray()

    def nxt():
        nonlocal x
        x ^= (x << 13) & 0xffffffff
        x ^= x >> 17
        x ^= (x << 5) & 0xffffffff
        return x
    for _ in range((n + 3) // 4):
        r = nxt()
        if pattern == 1:
            r &= nxt() & nxt()
        elif pattern == 2:
            r |= nxt() | nxt()
        elif pattern == 3:
            r &= nxt() & nxt() & nxt() & nxt()
        out += struct.pack('>I', r)
    return out[:n] if n % 4 == 0 else out


def run_model(regs, size, size2, mem):
    b = Blitter(**{k: regs[k] for k in FRB if k != 'size'})
    b.bold = 0
    b.bdat_write(regs['bdat'])
    rc = b.blit(mem, size)
    if size2 and not rc:
        rc = b.blit(mem, size2)
    return b, rc


def layout(regs, size, size2):
    """Pack the touched words into segments; return rebased regs, reloc, len."""
    m = Mem()
    _, rc = run_model(regs, size, size2, m)
    assert rc == 0, regs
    # One contiguous span per channel keeps its row geometry; overlapping or
    # adjacent spans (C = D, sources inside the bank) merge.
    spans = sorted((min(v), max(v) + 2) for v in m.touch.values())
    segs = []
    for lo, hi in spans:
        if segs and lo <= segs[-1][1] + 16:
            segs[-1][1] = max(segs[-1][1], hi)
        else:
            segs.append([lo, hi])
    cur = GUARD; place = []
    for lo, hi in segs:
        at = cur + ((lo - cur) & 3)
        place.append((lo, hi, at)); cur = at + (hi - lo) + GUARD
    line = regs['con1'] & 1
    out = dict(regs); reloc = 0
    for bit, (ch, use) in enumerate([('apt', 0x800), ('bpt', 0x400), ('cpt', 0x200), ('dpt', 0x100)]):
        if line and ch == 'apt':
            continue                    # line mode: APT is the error term
        if line and ch == 'bpt':
            out[ch] = 0; continue
        p = regs[ch] & ~1
        hit = next(((lo, at) for lo, hi, at in place if lo <= p < hi), None)
        if hit is None:
            out[ch] = 0                 # channel never addressed
            if not line and regs['con0'] & use:
                raise AssertionError(('unaddressed', ch, regs))
            continue
        out[ch] = hit[1] + p - hit[0] + (regs[ch] & 1)
        reloc |= 1 << bit
    # A further 512 bytes after the last guard are filled and compared too.
    return out, reloc, min(cur + 512, CHIP_LIMIT) if cur <= CHIP_LIMIT else cur


def record(regs, size, size2, seed, pattern, kind):
    out, reloc, n = layout(regs, size, size2)
    if n > CHIP_LIMIT:
        return None
    b = bytearray(REC)
    for k, off in FRB.items():
        if k == 'size':
            struct.pack_into('>H', b, off, size)
        elif k in ('cpt', 'bpt', 'apt', 'dpt'):
            struct.pack_into('>I', b, off, out[k] & 0xffffffff)
        else:
            struct.pack_into('>H', b, off, out[k] & 0xffff)
    struct.pack_into('>HHIIHH', b, 0x3c, size2, reloc, seed, n, pattern, kind)
    return bytes(b)


def captured():
    seen = set(); cases = []; stats = {}
    for sc in SCENES:
        p = R / f'tmp/step5/fr1-census-{sc}-030-50-bce/blits.bin'
        n = 0
        for b in parse(p):
            regs = {k: b[k] for k in ('con0', 'con1', 'afwm', 'alwm', 'apt', 'bpt', 'cpt', 'dpt', 'adat', 'bdat', 'cdat')}
            for k in ('amod', 'bmod', 'cmod', 'dmod'):
                regs[k] = b[k] & 0xffff
            size = (b['v'] & 1023) << 6 | (b['h'] & 63)
            out, reloc, ln = layout(regs, size, 0)
            key = (tuple(sorted(out.items())), size)
            n += 1
            if key in seen:
                continue
            seen.add(key)
            cases.append((regs, size, 0, 0))
        stats[sc] = n
    return cases, stats


def generated(rng):
    cases = []
    W = 48                              # bytes per row in generated layouts
    r16 = lambda: rng.getrandbits(16)

    def area(con0, con1, h, v, desc=False, mods=None, fw=None, lw=None, adat=None, bdat=None, cdat=None, size2=0, odd=0):
        mods = mods or [W - 2 * h] * 4
        base = 0x10000
        rows = (2 * h + max(0, max(mods))) * v + 4 * W
        regs = dict(con0=con0, con1=con1 | (2 if desc else 0), afwm=r16() if fw is None else fw,
                    alwm=r16() if lw is None else lw, adat=r16() if adat is None else adat,
                    bdat=r16() if bdat is None else bdat, cdat=r16() if cdat is None else cdat,
                    amod=mods[0] & 0xffff, bmod=mods[1] & 0xffff, cmod=mods[2] & 0xffff, dmod=mods[3] & 0xffff)
        start = [base + i * (rows + 256) for i in range(4)]
        if desc:
            start = [s + (v - 1) * (2 * h + max(0, m)) + 2 * (h - 1) for s, m in zip(start, mods)]
        regs.update(apt=start[0] | (odd & 1), bpt=start[1], cpt=start[2] | (odd >> 1 & 1), dpt=start[3])
        size = (v & 1023) << 6 | (h & 63)
        cases.append((regs, size, size2, 1))

    # Every minterm with all four channels, random shifts, both directions.
    for mt in range(256):
        for desc in (False, True):
            area(0x0f00 | mt | rng.randrange(16) << 12, rng.randrange(16) << 12, rng.randrange(1, 9), rng.randrange(1, 9), desc)
    # Every ASH/BSH pair, A and B shifted together (minterm $CA cookie-cut and $96 XOR).
    for ash in range(16):
        for bsh in range(16):
            mt = 0xca if (ash + bsh) & 1 else 0x96
            area(0x0f00 | mt | ash << 12, bsh << 12, rng.randrange(1, 6), rng.randrange(1, 5), (ash ^ bsh) & 2 == 2)
    # Channel subsets with every source disabled once (ADAT/BDAT/CDAT constants).
    for use in range(1, 16):
        for mt in (0xca, 0xe2, 0x1e, 0x6c, 0x0a, 0xfa, 0x3a, 0xfc, 0xc0, 0x30, 0xaa, 0xea, 0x2a, 0xf0, 0xcc):
            area(use << 8 | mt | rng.randrange(16) << 12, (0 if use & 4 else rng.randrange(16)) << 12,
                 rng.randrange(1, 7), rng.randrange(1, 6), rng.random() < 0.5)
    # B disabled with a shifted BDAT (B hold from the BLTBDAT write).
    for bsh in range(16):
        for desc in (False, True):
            area(0x0b00 | 0xcc | rng.randrange(16) << 12, bsh << 12, rng.randrange(1, 5), rng.randrange(1, 4), desc)
    # Masks: edges, zero and all-ones, one-word rows (both masks on one word).
    edges = [0, 0xffff, 0x8000, 0x0001, 0x7fff, 0xfffe, 0x00ff, 0xff00]
    for fw in edges:
        for lw in edges:
            area(0x0900 | 0xf0 | rng.randrange(16) << 12, 0, rng.choice([1, 2, 3]), 2, rng.random() < 0.5, fw=fw, lw=lw)
    # Fill: IFE, EFE, both (acts as EFE), FCI, both directions, D only and C+D.
    for fill in (0x08, 0x10, 0x18):
        for fci in (0, 4):
            for desc in (True, False):
                for use, mt in ((0x0300, 0xaa), (0x0100, 0xf0), (0x0d00, 0xca), (0x0900, 0xf0)):
                    for h in (1, 2, 5, 24):
                        area(use | mt | rng.randrange(16) << 12, fill | fci, h, rng.choice([1, 7, 103]), desc)
    # Sizes: widths 1-24 words, heights 1-200 rows, plus BLTSIZE zero fields.
    for h in range(1, 25):
        for v in (1, 2, 3, 17, 64, 103, 200):
            if 2 * h * v <= 4800:
                area(0x0fca | rng.randrange(16) << 12, rng.randrange(16) << 12, h, v, rng.random() < 0.3, mods=[0, 0, 0, 0])
    area(0x09f0, 0, 64, 3)                                   # h field 0: 64 words
    area(0x09f0, 0, 64, 2, True)
    area(0x01ff, 0, 1, 1024, mods=[0, 0, 0, 0])              # v field 0: 1024 rows
    area(0x0dca, 0, 1, 1024, True, mods=[0, 0, 0, 0])
    # Modulos: negative, re-reading a row, odd values (bit 0 ignored), odd pointers.
    for _ in range(40):
        h = rng.randrange(1, 6)
        mods = [rng.choice([-2 * h, -2 * h - 2, 1, 3, 2 * h + 1, 7, -1]) for _ in range(3)] + [rng.choice([0, 2, 5, -2 * h + 4])]
        area(0x0fca | rng.randrange(16) << 12, rng.randrange(16) << 12, h, rng.randrange(2, 6), rng.random() < 0.5,
             mods=mods, odd=rng.randrange(4))
    # D disabled: nothing may be written.
    for desc in (False, True):
        area(0x0eca, 0x1000, 4, 4, desc)
    # Continuation: a second BLTSIZE with no other register written.
    for desc in (False, True):
        for use in (0x0f00, 0x0b00, 0x0d00, 0x0100):
            h, v = rng.randrange(1, 6), rng.randrange(1, 5)
            area(use | 0xca | rng.randrange(16) << 12, rng.randrange(16) << 12, h, v, desc, size2=(rng.randrange(1, 5) << 6) | h)

    # Lines: HRM setup (ADAT $8000, masks $FFFF, width 2, B off) in every
    # octant, with and without SING, textures with every BSH, every start pixel.
    def line(x0, y0, x1, y1, mt=0xca, sing=False, tex=0xffff, bsh=0, size2=False):
        dx, dy = x1 - x0, y1 - y0
        adx, ady = abs(dx), abs(dy)
        # SUD set: x steps every pixel (AUL gives its direction), y only on
        # SIGN clear (SUL). SUD clear: the same with x and y exchanged.
        if adx >= ady:
            dmax, dmin = adx, ady
            sud, sul, aul = 1, dy < 0, dx < 0
        else:
            dmax, dmin = ady, adx
            sud, sul, aul = 0, dx < 0, dy < 0
        err = 4 * dmin - 2 * dmax
        con1 = 1 | (0x10 if sud else 0) | (0x08 if sul else 0) | (0x04 if aul else 0) | (0x02 if sing else 0)
        con1 |= 0x40 if err < 0 else 0
        con1 |= bsh << 12
        base = 0x20000
        addr = base + y0 * W + (x0 >> 3 & ~1)
        regs = dict(con0=(x0 & 15) << 12 | 0x0b00 | mt, con1=con1, afwm=0xffff, alwm=0xffff, adat=0x8000,
                    bdat=tex, cdat=0, apt=err & 0xffff, bpt=0, cpt=addr, dpt=addr,
                    amod=(4 * (dmin - dmax)) & 0xffff, bmod=(4 * dmin) & 0xffff, cmod=W, dmod=W)
        n = dmax + 1
        size = (n & 1023) << 6 | 2
        cases.append((regs, size, ((rng.randrange(1, 9) & 1023) << 6 | 2) if size2 else 0, 1))

    cx, cy = 190, 100
    for ang in range(0, 360, 5):
        L = rng.choice([1, 2, 3, 15, 40, 90])
        x1 = int(round(cx + L * math.cos(math.radians(ang))))
        y1 = int(round(cy + L * math.sin(math.radians(ang))))
        for sing in (False, True):
            line(cx + rng.randrange(-8, 8), cy, x1, y1, mt=rng.choice([0xca, 0x4a, 0xea, 0x2a, 0x0a]), sing=sing)
    for bsh in range(16):
        line(10, 10 + bsh, 200, 30 + bsh * 3, tex=r16(), bsh=bsh)
    for x0 in range(16):
        line(32 + x0, 50, 32 + x0 + rng.randrange(-30, 30), 50 + rng.randrange(-30, 30), sing=rng.random() < 0.5)
    for _ in range(60):
        line(rng.randrange(20, 360), rng.randrange(20, 180), rng.randrange(20, 360), rng.randrange(20, 180),
             mt=rng.randrange(256) & 0xfe | 0x0a if rng.random() < 0.3 else 0x4a, sing=rng.random() < 0.5,
             tex=r16(), bsh=rng.randrange(16), size2=rng.random() < 0.2)
    line(100, 100, 100, 100)                                 # single dot
    line(100, 100, 101, 100, sing=True)
    return cases


def main(out=None):
    out = Path(out) if out else R / 'tmp/build/fr2-data'
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(0xf2)
    cap, stats = captured()
    gen = generated(rng)
    blob = bytearray(); meta = []; dropped = 0
    for i, (regs, size, size2, kind) in enumerate(cap + gen):
        rec = record(regs, size, size2, rng.getrandbits(32) | 1, i % 4, kind)
        if rec is None:
            dropped += 1; continue
        blob += rec
        meta.append(dict(index=len(meta), kind=kind, size=size, size2=size2,
                         regs={k: v for k, v in regs.items()}))
    (out / 'FR2Cases.bin').write_bytes(blob)
    (out / 'cases.json').write_text(json.dumps(dict(captured_per_scene=stats, captured_unique=len(cap), generated=len(gen),
                                                    dropped_too_large=dropped, cases=meta), indent=0) + '\n')
    print('captured blits', stats, 'unique', len(cap), 'generated', len(gen), 'records', len(meta),
          'dropped', dropped, 'bytes', len(blob))
    return out


if __name__ == '__main__':
    main(*sys.argv[1:2])
