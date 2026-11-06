#!/usr/bin/env python3
"""FR12 host check of the merged car pass (FRCar in src/FastRender.s).

  fr12_car.py [CPU] [--cases N]      CPU 68020, 68030 (default) or 68040

Assembles FRCar alone (FRSpan and FRMarkSpan stubbed: every span is in a mirror
at +$40000), runs it under Unicorn on random cars (width, height, clipping, shift,
position, colour bits) and compares planes 0 and 1 with the native sequence on
tools/fr2_model.py's blitter: the mask blit (ABD $FC), the colour blit (the minterm
of the table at $32d48) and the cookie-cut (ABCD $CA) with the native registers.
Planes 0, 1 and 2 are compared, and the routine's end state: FRCar returns to its
rts ($32f0e) with d0, d1, a3, a5 and the colour argument words as the native loop
leaves them, every other register unchanged. Also checks the model of the merged
formula itself.
"""
import ctypes, os, random, re, struct, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fr2_model import Blitter, Mem
from fr2_unicorn import UC, U

R = Path(__file__).resolve().parents[1]
MT = {0: 0x0100, 1: 0x0dc0, 2: 0x0d30, 3: 0x09f0}     # the table at $32d48
FAST = 0x40000


def native(w, h, d3, d4, s, idx, p0, p1, screen, dst):
    """The native blits of one plane on the model; returns the screen words."""
    mem = bytearray(0x40000); m = Mem(mem)
    def put(a, ws):
        for i, v in enumerate(ws):
            mem[a + 2 * i] = v >> 8; mem[a + 2 * i + 1] = v & 255
    put(0x1000, p0); put(0x3000, p1); put(0x10000, screen)
    mask, col = 0x5000, 0x7000
    Blitter(con0=0x0dfc, afwm=0xffff, alwm=0xffff, apt=0x1000, bpt=0x3000, dpt=mask).blit(m, h << 6 | w)
    Blitter(con0=MT[idx], afwm=0xffff, alwm=0xffff, apt=0x3000, bpt=0x1000, dpt=col).blit(m, h << 6 | w)
    amod = (d3 + d4 - 1) * 2; cmod = amod - 2 * w + 0x30
    Blitter(con0=s << 12 | 0x0fca, con1=s << 12, afwm=0 if d4 else 0xffff, alwm=0, amod=amod, bmod=amod,
            cmod=cmod, dmod=cmod, apt=mask + 2 * d4, bpt=col + 2 * d4, cpt=0x10000 + dst,
            dpt=0x10000 + dst).blit(m, ((h << 6 | w) + 1 - d3 - d4) & 0xffff)
    return [mem[0x10000 + 2 * i] << 8 | mem[0x10001 + 2 * i] for i in range(len(screen))]


def merged(w, h, d3, d4, s, idx, p0s, p1s, screen, dst):
    """The merged formula: D = (C & ~M) | colour, M and colour from P1 and P0 shifted once."""
    scr = list(screen); bw = (w + 1 - d3 - d4) & 63
    for r in range(h):
        h1 = h0 = 0
        for j in range(bw):
            p1 = p0 = 0
            if j < bw - 1 and not (j == 0 and d4):
                p1 = p1s[d4 + r * w + j]; p0 = p0s[d4 + r * w + j]
            h1 = (h1 & 0xffff) << 16 | p1; h0 = (h0 & 0xffff) << 16 | p0
            a = h1 >> s & 0xffff; b = h0 >> s & 0xffff
            k = dst // 2 + r * 24 + j
            scr[k] = scr[k] & ~(a | b) & 0xffff | [0, a & b, a & ~b & 0xffff, a][idx]
    return scr


def assemble():
    d = R / 'tmp/build/fr12-car'; d.mkdir(parents=True, exist_ok=True)
    s = (R / 'src/FastRender.s').read_text()
    body = s[s.index('FRC_ROWS equ'):s.index('FRT6bbe6:')].replace('$226ae', 'FRTestTable')
    (d / 'w.s').write_text(' org $1000\nFR12S_MERGED equ 4\nFR12S_NATIVE equ 8\nentry:\n bsr.w FRCar\n'
                           'entry_end:\n jmp $32f0e\nFRSpan:\n moveq #2,d1\n move.l #$40000,d0\n rts\n'
                           'FRMarkSpan:\n rts\nFF1FastRenderSize:\n rts\nFRSITE_32DFA equ 5\nFRCarDeferred: dc.w 1\n'
                           'FF1FastRenderCarStats: dc.l 0,0,0\nFRTestTable: dc.l 0\n' + body)
    vasm = os.environ.get('VASM', str(Path.home() / '.local/vasmm68k_mot'))
    subprocess.run([vasm, '-m68020', '-Fbin', '-quiet', '-L', 'w.list', '-o', 'w.bin', 'w.s'], cwd=d, check=True)
    sy = {n: int(v, 16) for n, v in re.findall(r'^(\w+)\s+A:([0-9A-F]{8})$', (d / 'w.list').read_text(), re.M)}
    return (d / 'w.bin').read_bytes(), sy


def main():
    cpu = next((a for a in sys.argv[1:] if a.startswith('680')), '68030')
    n = int(sys.argv[sys.argv.index('--cases') + 1]) if '--cases' in sys.argv else 3000
    code, sy = assemble()
    assert 0x1000 + len(code) <= 0xc000, 'FRCar overlaps the test data'
    rng = random.Random(12); cases = bad = formula = 0
    while cases < n:
        w = rng.randint(1, 24); h = rng.randint(1, 12)
        d4 = rng.choice([0, 0, 1, 2, 5]); d3 = rng.choice([0, 0, 1, 2, 7])
        if w + 1 - d3 - d4 < 2:
            continue
        s = rng.randint(0, 15); cx = rng.getrandbits(3); cy = rng.getrandbits(3)
        p0 = [rng.getrandbits(16) for _ in range(w * h + 4)]
        p1 = [rng.getrandbits(16) for _ in range(w * h + 4)]
        scr = [[rng.getrandbits(16) for _ in range(24 * (h + 2) + 40)] for _ in range(3)]
        x = rng.randint(0, 12); y = rng.randint(0, 1); off = d4 + 24 * y + x
        u = UC(cpu); u.w(0x1000, code); u.w(sy['FRTestTable'], struct.pack('>I', 0xd000))
        u.w(0xc000, struct.pack('>HHHHHHII', w, h, 0, 0, 0, 0, 0x10000, 0x12000))
        u.w(0xd000, struct.pack('>III', 0x20000, 0x22000, 0x24000))
        u.w(0x10000 + FAST, struct.pack(f'>{len(p0)}H', *p0))
        u.w(0x12000 + FAST, struct.pack(f'>{len(p1)}H', *p1))
        for p in range(3):
            u.w(0x20000 + 0x2000 * p + FAST, struct.pack(f'>{len(scr[p])}H', *scr[p]))
        sp = 0x7f000      # native a7: the colour bits at $12 (after the native lsl) and $16
        u.w(sp + 0x12, struct.pack('>H', cx << 1)); u.w(sp + 0x16, struct.pack('>H', cy))
        regs = dict(a0=0xc000, a1=0x5000, a3=0, a4=h << 6 | w, d3=d3, d4=d4, d5=s << 12, d6=x, d7=24 * y,
                    d0=0x12345678, d1=0xabcd0000, d2=0x55550000)
        for k, v in regs.items():
            u.reg(k, v)
        u.reg('sr', 0x2700); u.reg('a7', sp)
        u.w(sp - 4, struct.pack('>I', sy['entry_end']))     # FRCar is entered by a jsr from the routine
        u.reg('a7', sp - 4)
        rc = U.uc_emu_start(u.h, ctypes.c_uint64(sy['FRCar']), ctypes.c_uint64(0x32f0e),
                            ctypes.c_uint64(0), ctypes.c_size_t(0))
        if rc:
            print('emulation error', rc, hex(u.reg('pc')), dict(w=w, h=h, d3=d3, d4=d4, s=s, x=x, y=y)); return 1
        cases += 1
        bw = w + 1 - d3 - d4
        ok = u.reg('pc') == 0x32f0e and u.reg('a7') == sp and u.reg('a3') == 3 \
            and u.reg('a5') == 0x24000 + 2 * off and u.reg('d0') == 0xffff0000 | ((h << 6 | w) + 1 - d3 - d4) \
            and u.reg('d1') == 0xabcd0000 | (cy >> 2 & 1) \
            and u.r(sp + 0x12, 2) == struct.pack('>H', (cx << 1) >> 3) and u.r(sp + 0x16, 2) == struct.pack('>H', cy >> 3) \
            and all(u.reg(k) == v for k, v in regs.items() if k not in ('a3', 'd0', 'd1'))
        if not ok and bad < 3:
            print('state', {k: hex(u.reg(k)) for k in ('pc', 'a7', 'a3', 'a5', 'd0', 'd1')})
        for p in range(3):
            idx = (cx >> p & 1) * 2 + (cy >> p & 1)     # bit p of each colour argument
            exp = native(w, h, d3, d4, s, idx, p0, p1, scr[p], 2 * off)
            formula += exp != merged(w, h, d3, d4, s, idx, p0, p1, scr[p], 2 * off)
            got = list(struct.unpack(f'>{len(scr[p])}H', u.r(0x20000 + 0x2000 * p + FAST, 2 * len(scr[p]))))
            ok &= exp == got
        if not ok:
            bad += 1
            if bad <= 3:
                print('mismatch', dict(w=w, h=h, d3=d3, d4=d4, s=s, cx=cx, cy=cy, x=x, y=y))
    print(f'{cpu} cases {cases} mismatches {bad} formula mismatches {formula}')
    return 1 if bad or formula else 0


if __name__ == '__main__':
    sys.exit(main())
