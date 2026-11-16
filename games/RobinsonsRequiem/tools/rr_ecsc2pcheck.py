#!/usr/bin/env python3
"""The ECS chunky-to-planar conversion against START's: rr_ecsc2pcheck.py [CASES] [SEED]

Runs START's loop (hunk 2 +$1a5e to +$1b98, from tmp/game/RobinsonsRequiem/data-ecs/START,
hunk 2 loaded at address 0 so that its chunky modulo at +$46 resolves), src/c2p000.s's
_c2p000 (68000), src/c2pblit.s's _c2pblit (68000, with the blitter) and src/c2p020.s's
_c2p020 (68020) under Unicorn on the same random rectangles, chunky bytes and plane
contents, and compares the four planes byte for byte. Rectangles: widths of 16 to 320
pixels in 16-pixel steps, 1 to 200 rows (_c2pblit's streams take 320 x 100 or 256 x 125;
larger rectangles go to _c2p000), a left edge on 16 pixels, chunky strides of the
width up to 336 bytes, START's 40-byte plane rows; planes 0 and 2 each with its pair 16,000
bytes on. _c2pblit's blits run in a model of the blitter (the Hardware Reference Manual's
channels, shifts, masks, minterms, modulos and descending mode) when BLTSIZE is written,
each with random words in the shifters and every register the routine does not write
random, its streams in memory with random bytes; DMACONR reads as idle. The model is
checked first against hand-worked blits. Exit status 1 on the first difference.
"""
import ctypes
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rr_c2pcheck import Machine, UC_CPU_M68K_M68000, UC_CPU_M68K_M68020, hunk  # noqa: E402

CUSTOM = 0xdff000
CBBUF, CBTAB = 0x400000, 0x480000
UC_HOOK_MEM_WRITE = 1 << 11
HOOK = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_uint64, ctypes.c_int,
                        ctypes.c_int64, ctypes.c_void_p)


def blit(read, write, r, rnd):
    """One blit from the register words r (offset from $dff000: value): area mode only."""
    con0, con1, size = r[0x40], r[0x42], r[0x58]
    assert not con1 & 1, 'line mode'
    h, w = (size >> 6) or 1024, (size & 63) or 64
    use, lf = con0 >> 8 & 15, con0 & 0xff
    ash, bsh, desc = con0 >> 12, con1 >> 12, bool(con1 & 2)
    step = -2 if desc else 2
    pt = {c: (r[o] << 16 | r[o + 2]) & 0xfffffe for c, o in
          (('a', 0x50), ('b', 0x4c), ('c', 0x48), ('d', 0x54))}
    mod = {'a': r[0x64], 'b': r[0x62], 'c': r[0x60], 'd': r[0x66]}
    mod = {c: (m ^ 0x8000) - 0x8000 & ~1 for c, m in mod.items()}
    dat = {'a': r[0x74], 'b': r[0x72], 'c': r[0x70]}
    prev = {'a': rnd.getrandbits(16), 'b': rnd.getrandbits(16)}
    for _ in range(h):
        for i in range(w):
            for c, bit in (('a', 8), ('b', 4), ('c', 2)):
                if use & bit:
                    dat[c] = read(pt[c])
                    pt[c] += step
            a = dat['a']
            if i == 0:
                a &= r[0x44]
            if i == w - 1:
                a &= r[0x46]
            sh = {}
            for c, v, s in (('a', a, ash), ('b', dat['b'], bsh)):
                if desc:
                    sh[c] = (v << s | prev[c] >> (16 - s)) & 0xffff
                else:
                    sh[c] = (prev[c] << 16 | v) >> s & 0xffff
                prev[c] = v
            av, bv, cv = sh['a'], sh['b'], dat['c']
            d = 0
            for t in range(8):
                if lf >> t & 1:
                    d |= ((av if t & 4 else ~av) & (bv if t & 2 else ~bv)
                          & (cv if t & 1 else ~cv))
            if use & 1:
                write(pt['d'], d & 0xffff)
                pt['d'] += step
        for c, bit in (('a', 8), ('b', 4), ('c', 2), ('d', 1)):
            if use & bit:
                pt[c] += -mod[c] if desc else mod[c]


def check_blit_model():
    """The model on blits worked by hand: a copy, a right and a left shift, a minterm."""
    mem = {}
    read = lambda a: mem.get(a, 0)  # noqa: E731

    def write(a, v):
        mem[a] = v
    rnd = random.Random(0)
    base = {o: 0 for o in range(0x48, 0x58, 2)}
    base.update({0x44: 0xffff, 0x46: 0xffff, 0x60: 0, 0x62: 0, 0x64: 0, 0x66: 0, 0x70: 0,
            0x72: 0, 0x74: 0})
    for i, v in enumerate([0x1234, 0x5678, 0x9abc]):
        mem[0x1000 + 2 * i] = v
    r = {**base, **{0x40: 0x09f0, 0x42: 0, 0x50: 0, 0x52: 0x1000, 0x54: 0, 0x56: 0x2000,
                      0x58: 1 << 6 | 3}}
    blit(read, write, r, rnd)
    assert [mem[0x2000 + 2 * i] for i in range(3)] == [0x1234, 0x5678, 0x9abc]
    # B shifted right by 4 into D, ascending; the first word's top nibble from the shifter
    r = {**base, **{0x40: 0x05cc, 0x42: 0x4000, 0x4c: 0, 0x4e: 0x1000, 0x54: 0,
                      0x56: 0x3000, 0x58: 1 << 6 | 3}}
    blit(read, write, r, rnd)
    assert [mem[0x3000 + 2 * i] & m for i, m in enumerate([0x0fff, 0xffff, 0xffff])] == \
        [0x0123, 0x4567, 0x89ab]
    # the same descending: a left shift by 4, from the last word back
    r = {**base, **{0x40: 0x05cc, 0x42: 0x4002, 0x4c: 0, 0x4e: 0x1004, 0x54: 0,
                      0x56: 0x4004, 0x58: 1 << 6 | 3}}
    blit(read, write, r, rnd)
    assert [mem[0x4000 + 2 * i] & m for i, m in enumerate([0xffff, 0xffff, 0xfff0])] == \
        [0x2345, 0x6789, 0xabc0]
    # D = A & C | B & ~C (LF $e4), C a constant, two rows with modulos
    for i, v in enumerate([0xffff, 0, 0xffff, 0]):
        mem[0x5000 + 2 * i] = v
    for i, v in enumerate([0, 0xffff, 0, 0xffff]):
        mem[0x6000 + 2 * i] = v
    r = {**base, **{0x40: 0x0de4, 0x42: 0, 0x50: 0, 0x52: 0x5000, 0x4c: 0, 0x4e: 0x6000,
                      0x54: 0, 0x56: 0x7000, 0x70: 0x00ff, 0x64: 2, 0x62: 2, 0x66: 2,
                      0x58: 2 << 6 | 1}}
    blit(read, write, r, rnd)
    assert [mem.get(0x7000 + 2 * i) for i in range(3)] == [0x00ff, None, 0x00ff]
    # D = A & ~C | B & C (LF $d8)
    mem[0x8000], mem[0x8002] = 0x1234, 0xabcd
    r = {**base, **{0x40: 0x0dd8, 0x42: 0, 0x50: 0, 0x52: 0x8000, 0x4c: 0, 0x4e: 0x8002,
                    0x54: 0, 0x56: 0x8004, 0x70: 0x0f0f, 0x58: 1 << 6 | 1}}
    blit(read, write, r, rnd)
    assert mem[0x8004] == 0x1b3d


class BlitMachine(Machine):
    """A Machine with the custom chips' page: blitter register writes kept, blits at BLTSIZE."""

    def __init__(self, cpu, rnd):
        super().__init__(cpu)
        uc = self.uc
        assert uc.uc_mem_map(self.h, CUSTOM, 0x1000, 3) == 0
        self.rnd = rnd
        self.r = {o: rnd.getrandbits(16) for o in range(0x40, 0x78, 2)}
        self.blits = 0
        uc.uc_hook_add.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                                   ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_uint64, ctypes.c_uint64]
        self.cb = HOOK(self.hook)
        hh = ctypes.c_size_t()
        assert uc.uc_hook_add(self.h, ctypes.byref(hh), UC_HOOK_MEM_WRITE,
                              ctypes.cast(self.cb, ctypes.c_void_p), None, CUSTOM,
                              CUSTOM + 0xfff) == 0

    def hook(self, _uc, _type, addr, size, value, _user):
        off = addr - CUSTOM
        for i in range(0, size, 2):
            self.r[off + i] = (value >> (8 * (size - 2 - i))) & 0xffff
        if off <= 0x58 < off + size:
            self.blits += 1
            blit(lambda a: struct.unpack('>H', self.read(a, 2))[0],
                 lambda a, v: self.write(a, struct.pack('>H', v)), self.r, self.rnd)

ROOT = Path(__file__).resolve().parents[1]
START = ROOT / 'tmp/game/RobinsonsRequiem/data-ecs/START'
CODE_NEW, STACK = 0x700000, 0x7D0000
CHUNKY = 0x100000
P0, P2 = 0x200000, 0x300000
AREAS = [(P0, 0x10000), (P2, 0x10000)]
ROWLEN, BPL = 40, 16000
LOOP, END, MODC = 0x1a5e, 0x1b98, 0x46


def assemble(entry, cpu):
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'c2p.s', tmp / 'c2p.bin'
    s.write_text(f'\t\tORG\t${CODE_NEW:x}\n\t\tbra.w\tc2pentry\n_c2pmod\tdc.l\t${MODC:x}\n'
                 f'MEMF_PUBLIC\t= 1\nMEMF_CHIP\t= 2\n_LVOAllocMem\t= -198\n'
                 f'_LVOFreeMem\t= -210\n'
                 f'c2pentry\tmovem.l\td0-a6,-(a7)\n'
                 f'\t\tlea\t_cbbuf(pc),a5\n\t\tmove.l\t#${CBBUF:x},(a5)\n'
                 f'\t\tlea\t_cbtab(pc),a5\n\t\tmove.l\t#${CBTAB:x},(a5)\n'
                 f'\t\tbra\t{entry}\n'
                 f'\t\tINCLUDE\t"{ROOT / "src/c2p000.s"}"\n'
                 f'\t\tINCLUDE\t"{ROOT / "src/c2pblit.s"}"\n'
                 f'\t\tINCLUDE\t"{ROOT / "src/c2p020.s"}"\n')
    subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), f'-m{cpu}', '-devpac', '-Fbin',
                    '-quiet', '-o', str(b), str(s)], check=True)
    data = b.read_bytes()
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return data


def main():
    cases = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    check_blit_model()
    code = hunk(2, START)
    news = [(name, assemble(name, cpu), uc) for name, cpu, uc in
            (('_c2p000', '68000', UC_CPU_M68K_M68000), ('_c2pblit', '68000', UC_CPU_M68K_M68000),
             ('_c2p020', '68020', UC_CPU_M68K_M68020))]
    blits = blitted = 0
    for n in range(cases):
        w = 16 * rnd.randrange(1, 21)
        x0 = 16 * rnd.randrange(0, (320 - w) // 16 + 1)
        rows = rnd.choice([1, 2, 100, 125, rnd.randrange(1, 101), rnd.randrange(1, 201)])
        y0 = rnd.randrange(0, 200 - rows + 1)
        stride = rnd.choice([320, 336, x0 + w + 2 * rnd.randrange(0, 9)])
        chunky = rnd.randbytes(stride * (rows + 2) + 64)
        planes = [rnd.randbytes(size) for _, size in AREAS]
        off = y0 * ROWLEN + x0 // 8
        regs = [rnd.getrandbits(32) for _ in range(16)]
        regs[6] = (regs[6] & 0xffff0000) | (w // 16 - 1)
        regs[7] = (regs[7] & 0xffff0000) | (rows - 1)
        regs[8] = CHUNKY + x0
        regs[9], regs[10] = P0 + off, P2 + off
        regs[14] = (regs[14] & 0xffff0000) | (ROWLEN - w // 8)
        regs[15] = STACK
        out, names = [], ['START']
        for target, until, new, cpu in [(LOOP, END, b'', UC_CPU_M68K_M68000)] + \
                [(CODE_NEW, None, n, c) for _, n, c in news]:
            m = BlitMachine(cpu, rnd)
            m.write(CBBUF, rnd.randbytes(2 * 16000))
            m.write(CBTAB, rnd.randbytes(512))
            m.write(0, code)
            m.write(MODC, struct.pack('>h', stride - w))
            m.write(CODE_NEW, new)
            m.write(CHUNKY, chunky)
            for (a, _), data in zip(AREAS, planes):
                m.write(a, data)
            m.call(target, regs, until)
            blits += m.blits
            blitted += m.blits > 0
            out.append([m.read(a, size) for a, size in AREAS])
        if out[0] == planes:
            sys.exit(f'case {n}: the planes did not change')
        for (name, _, _), got in zip(news, out[1:]):
            if out[0] == got:
                continue
            for (a, _), x, y in zip(AREAS, out[0], got):
                for i in range(len(x)):
                    if x[i] != y[i]:
                        print(f'case {n}: w {w} x0 {x0} rows {rows} y0 {y0} stride {stride}: '
                              f'first difference at {a + i:#x}: START {x[i]:02x}, '
                              f'{name} {y[i]:02x}')
                        sys.exit(1)
    print(f'{cases} cases identical for ' + ', '.join(n for n, _, _ in news)
          + f' ({blitted} of them by _c2pblit\'s blits, {blits} blits; the rest larger than '
          'its streams, by _c2p000)')


if __name__ == '__main__':
    main()
