#!/usr/bin/env python3
"""Differential check of 2.0b's merged plotters (src/Enhanced.s) against the original loops.

    python3 tools/plotcheck.py [DUMP] [N]

DUMP is a chip dump with the program at $400 (default tmp/dumps/attract.bin, from 1.3 or 2.0b
without fast memory); N random cases per routine (default 2000). Each case runs the original
loop (from the dump) and the slave's replacement (assembled from Enhanced.s) in Unicorn's
68020 from the same registers and memory, and compares every data and address register, the
condition codes, the screen and the stack from the stack pointer up. _PlotColumn runs with _GfxDelta 0 and with a
fast copy of the graphics that differs in the buggy's planes (as a stale copy would), with
sources inside, partly outside alloc 2, and over the buggy.
"""
import ctypes
import os
import random
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UC_ARCH_M68K, UC_MODE_BIG_ENDIAN = 7, 1 << 30
UC_CTL_CPU_MODEL, UC_CPU_M68K_M68020 = 7, 2
REG_A0, REG_D0, REG_SR, REG_PC = 1, 9, 17, 18
MEM = 0x800000
CODE_ORIG, CODE_NEW, SENTINEL = 0x700000, 0x710000, 0x7F0000
STACK = 0x7E0000
SR_SAVE = 0x7CF000
SCREEN, GFX, COPY = 0x100000, 0x200000, 0x300000   # alloc 2 and its fast copy
GFX_SIZE, GFX_BUGGY, BUGGY_BYTES = 240000, 0xD3A8, 1600

# The original loops: program offset, end (exclusive), and whether an rts must be appended.
ORIGINAL = {'column': (0x3DC4, 0x3E52, False), 'buggy': (0x41A4, 0x41E2, False),
            'text': (0x4A94, 0x4AD8, True)}


def load_unicorn():
    lib = Path(os.environ.get('AMIGA_UNICORN', Path.home() / '.local/share/amiga/unicorn'))
    uc = ctypes.CDLL(str(lib / 'lib/libunicorn.2.dylib'))
    uc.uc_reg_write.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    uc.uc_reg_read.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    uc.uc_mem_write.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_char_p, ctypes.c_size_t]
    uc.uc_mem_read.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t]
    uc.uc_mem_map.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_size_t, ctypes.c_uint32]
    uc.uc_emu_start.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64,
                                ctypes.c_uint64, ctypes.c_size_t]
    uc.uc_ctl.argtypes = [ctypes.c_void_p, ctypes.c_int]   # variadic: the rest as c types
    return uc


def assemble():
    """The plotters and their variables from Enhanced.s, as a raw binary at CODE_NEW."""
    src = (ROOT / 'src/Enhanced.s').read_text()
    start = re.search(r'^_PlotColumn\t', src, re.M).start()
    end = src.index('; Before the race loop')
    body = src[start:end]
    consts = '\n'.join(re.findall(r'^(?:GFX_BUGGY|BUGGY_BYTES)\t.*$', src, re.M))
    # a branch table at 0, 4, 8 and the variables at 12 (in _GfxLo's order)
    text = (f'\t\tORG\t${CODE_NEW:x}\n{consts}\n'
            '\t\tbra.w\t_PlotColumn\n\t\tbra.w\t_PlotBuggy\n\t\tbra.w\t_PlotText\n'
            '_GfxLo\tdc.l\t0\n_GfxHi\tdc.l\t0\n_GfxRace\tdc.l\t0\n_GfxDelta\tdc.l\t0\n'
            f'{body}\n')
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'plot.s', tmp / 'plot.bin'
    s.write_text(text)
    vasm = os.environ.get('VASM', 'vasmm68k_mot')
    subprocess.run([vasm, '-m68020', '-devpac', '-Fbin', '-quiet', '-o', str(b), str(s)], check=True)
    syms = {'_PlotColumn': CODE_NEW, '_PlotBuggy': CODE_NEW + 4, '_PlotText': CODE_NEW + 8,
            '_GfxLo': CODE_NEW + 12}
    data = b.read_bytes()
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()
    return data, syms


class Machine:
    def __init__(self, uc):
        self.uc = uc
        h = ctypes.c_void_p()
        assert uc.uc_open(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, ctypes.byref(h)) == 0
        self.h = h
        assert uc.uc_ctl(h, UC_CTL_CPU_MODEL | (1 << 26) | (1 << 30),
                         ctypes.c_int(UC_CPU_M68K_M68020)) == 0
        assert uc.uc_mem_map(h, 0, MEM, 7) == 0

    def write(self, addr, data):
        assert self.uc.uc_mem_write(self.h, addr, bytes(data), len(data)) == 0

    def read(self, addr, n):
        buf = ctypes.create_string_buffer(n)
        assert self.uc.uc_mem_read(self.h, addr, buf, n) == 0
        return buf.raw

    def reg(self, r, v=None):
        x = ctypes.c_uint32(v if v is not None else 0)
        if v is None:
            self.uc.uc_reg_read(self.h, r, ctypes.byref(x))
            return x.value
        self.uc.uc_reg_write(self.h, r, ctypes.byref(x))

    def run(self, pc, regs, sr):
        self.reg(REG_SR, sr)                 # SR before A7 (the active stack pointer)
        for i in range(8):
            self.reg(REG_D0 + i, regs[i])
        for i in range(8):
            self.reg(REG_A0 + i, regs[8 + i])
        err = self.uc.uc_emu_start(self.h, pc, SENTINEL, 0, 0)
        if err:
            raise RuntimeError(f'emulation error {err} at pc {self.reg(REG_PC):#x} from {pc:#x}')
        # Unicorn's SR read does not bring the lazily computed flags up to date: the stub
        # stores SR with move.w sr (stub())
        ccr = int.from_bytes(self.read(SR_SAVE, 2), 'big') & 0x1F
        return ([self.reg(REG_D0 + i) for i in range(8)] + [self.reg(REG_A0 + i) for i in range(8)],
                ccr)


def stub(target):
    """jsr target; move.w sr,SR_SAVE; jmp SENTINEL"""
    return (b'\x4e\xb9' + target.to_bytes(4, 'big') + b'\x40\xf9' + SR_SAVE.to_bytes(4, 'big')
            + b'\x4e\xf9' + SENTINEL.to_bytes(4, 'big'))


def case(kind, rnd, syms):
    """Registers and the memory changes for one random case."""
    r = [rnd.getrandbits(32) for _ in range(16)]
    mem = []
    gfx = rnd.randbytes(GFX_SIZE)
    mem.append((GFX, gfx))
    delta = 0
    if kind == 'column':
        delta = rnd.choice([0, COPY - GFX])
        stale = bytearray(gfx)               # the copy differs in the buggy's planes, as if stale
        for k in range(4):
            o = GFX_BUGGY + 8000 * k
            stale[o:o + BUGGY_BYTES] = rnd.randbytes(BUGGY_BYTES)
        mem.append((COPY, bytes(stale)))
        rows = rnd.choice([1, 2, rnd.randrange(1, 80)])
        stride = rnd.choice([2, 42])
        lo_min = GFX + (rows - 1) * (stride - 2)
        where = rnd.random()
        if where < 0.15:                     # over the buggy (from chip)
            src = GFX + GFX_BUGGY + rnd.randrange(-8000, 8000) + rnd.choice([0, 8000, 16000])
        elif where < 0.25:                   # partly outside alloc 2
            src = GFX + GFX_SIZE - 24002 + rnd.randrange(-40, 400)
        else:
            src = rnd.randrange(lo_min, GFX + GFX_SIZE - 24002)
        r[9] = src & ~1                      # a1
        r[8] = (SCREEN + rnd.randrange(rows * 40 + 40, 7900)) & ~1
        r[10] = r[8] + 2                     # a2
        r[11] = 0x7D0000                     # a3 -> the stride word
        mem.append((0x7D0000, stride.to_bytes(2, 'big')))
        r[4] = (r[4] & 0xFFFF0000) | (rows - 1)
        r[6] = (r[6] & 0xFFFFFF00) | rnd.randrange(1, 17)
    elif kind == 'buggy':
        r[8] = (SCREEN + rnd.randrange(0, 8000 - 1600 - 16)) & ~1
        r[9] = GFX + GFX_BUGGY
    else:
        r[8] = (SCREEN + rnd.randrange(0, 8000 - 320)) & ~1
        r[9] = (0x7C0000 + rnd.randrange(0, 0x8000)) & ~1
        r[10] = (0x7C8000 + rnd.randrange(0, 0x8000)) & ~1
        mem.append((0x7C0000, rnd.randbytes(0x10000)))
    mem.append((SCREEN, rnd.randbytes(32000 + 64)))
    r[15] = STACK
    var = bytearray(16)
    var[0:4] = GFX.to_bytes(4, 'big')
    var[4:8] = (GFX + GFX_SIZE).to_bytes(4, 'big')
    var[8:12] = (COPY - GFX).to_bytes(4, 'big')
    var[12:16] = delta.to_bytes(4, 'big')
    mem.append((syms['_GfxLo'], bytes(var)))
    return r, mem, rnd.getrandbits(5)


def main(argv):
    dump = Path(argv[0]) if argv else ROOT / 'tmp/dumps/attract.bin'
    n = int(argv[1]) if len(argv) > 1 else 2000
    prog = dump.read_bytes()[0x400:]
    new, syms = assemble()
    entry = {'column': syms['_PlotColumn'], 'buggy': syms['_PlotBuggy'], 'text': syms['_PlotText']}
    uc = load_unicorn()
    m = Machine(uc)
    orig_at = {}
    at = CODE_ORIG
    for k, (a, b, rts) in ORIGINAL.items():
        code = prog[a:b] + (b'\x4e\x75' if rts else b'')
        m.write(at, code)
        orig_at[k] = at
        at += (len(code) + 15) & ~15
    m.write(CODE_NEW, new)
    stubs = {}
    for k in ORIGINAL:
        stubs[k] = []
        for target in (orig_at[k], entry[k]):
            m.write(at, stub(target))
            stubs[k].append(at)
            at += 32
    rnd = random.Random(1988)
    bad = 0
    snap = [(SCREEN, 32064)]          # the stack: below the stack pointer is dead after the return
    for kind in ORIGINAL:
        fails = 0
        for i in range(n):
            regs, mem, ccr = case(kind, rnd, syms)
            results = []
            for pc in stubs[kind]:
                for addr, data in mem:
                    m.write(addr, data)
                m.write(STACK - 0x100, bytes(0x100))
                m.write(SR_SAVE, bytes(2))
                st = m.run(pc, regs[:15] + [STACK], 0x2700 | ccr)
                results.append((st, [m.read(a, s) for a, s in snap]))
            (ro, mo), (rn, mn) = results
            if ro != rn or mo != mn:
                fails += 1
                if fails <= 3:
                    names = [f'd{i}' for i in range(8)] + [f'a{i}' for i in range(8)]
                    diff = [(names[j], hex(x), hex(y)) for j, (x, y) in enumerate(zip(ro[0], rn[0])) if x != y]
                    print(f'{kind} case {i}: regs {diff} ccr {ro[1]:#x}/{rn[1]:#x} '
                          f'memory {"same" if mo == mn else "differs"}')
        print(f'{kind}: {n} cases, {fails} differ')
        bad += fails
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
