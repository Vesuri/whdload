#!/usr/bin/env python3
"""The AGA chunky-to-planar conversion against START's: rr_c2pcheck.py [CASES] [SEED]

Runs START's loop (hunk 2 +$2e84, from tmp/game/RobinsonsRequiemAGA/data-aga/START, hunk 2
loaded at address 0 so that its own variables resolve) and src/c2p030.s's _c2p030 under
Unicorn (68020) on the same random rectangles, chunky bytes and plane contents, and compares
all eight planes byte for byte. Rectangles: widths of 16 to 320 pixels in 16-pixel steps
(the odd multiples of 16 take _c2p030's way back into START's loop), 1 to 200 rows, a left
edge on 16 pixels, START's 80-byte plane rows and 16,000-byte plane pairs; planes 0-1 in a
block of their own as in the game, planes 4-5 and 6-7 either after 2-3 (the game's layout)
or in blocks of their own. Exit status 1 on the first difference.
"""
import ctypes
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = ROOT / 'tmp/game/RobinsonsRequiemAGA/data-aga/START'
UC_ARCH_M68K, UC_MODE_BIG_ENDIAN = 7, 1 << 30
UC_CTL_CPU_MODEL, UC_CPU_M68K_M68000, UC_CPU_M68K_M68020 = 7, 1, 2
REG_A0, REG_D0, REG_SR, REG_PC = 1, 9, 17, 18
MEM = 0x800000
CODE_NEW, SENTINEL, STUB, STACK = 0x700000, 0x7F0000, 0x7E0000, 0x7D0000
CHUNKY = 0x100000
P0, P2, P4, P6 = 0x200000, 0x300000, 0x340000, 0x380000
AREAS = [(P0, 0x10000), (P2, 0x20000), (P4, 0x10000), (P6, 0x10000)]
ROWLEN, BPL = 80, 16000
LOOP, MODC, MODP = 0x2e84, 0x2db2, 0x2db4


def hunk(which=2, path=START):
    """START's hunk `which`, as loaded (relocations into the hunk itself are offsets from 0)."""
    d = Path(path).read_bytes()
    p = 0

    def word():
        nonlocal p
        p += 4
        return struct.unpack('>I', d[p - 4:p])[0]
    assert word() == 0x3f3
    while word():
        pass
    n, first, last = word(), word(), word()
    for _ in range(n):
        word()
    hunks = []
    while p < len(d):
        t = word() & 0x3fffffff
        if t in (0x3e9, 0x3ea):
            size = word() * 4
            hunks.append(d[p:p + size])
            p += size
        elif t == 0x3eb:
            word()
            hunks.append(b'')
        elif t == 0x3ec:
            while True:
                c = word()
                if not c:
                    break
                word()
                p += 4 * c
        elif t != 0x3f2:
            raise ValueError(f'hunk type {t:#x}')
    return hunks[which]


def assemble():
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'c2p.s', tmp / 'c2p.bin'
    s.write_text(f'\t\tORG\t${CODE_NEW:x}\n\t\tbra.w\t_c2p030\n_hunk2\tdc.l\t0\n'
                 f'\t\tINCLUDE\t"{ROOT / "src/c2p030.s"}"\n')
    subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), '-m68020', '-devpac', '-Fbin',
                    '-quiet', '-o', str(b), str(s)], check=True)
    data = b.read_bytes()
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return data


class Machine:
    def __init__(self, cpu=UC_CPU_M68K_M68020):
        lib = Path(os.environ.get('AMIGA_UNICORN', Path.home() / '.local/share/amiga/unicorn'))
        uc = self.uc = ctypes.CDLL(str(lib / 'lib/libunicorn.2.dylib'))
        uc.uc_reg_write.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        uc.uc_reg_read.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        uc.uc_mem_write.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_char_p,
                                    ctypes.c_size_t]
        uc.uc_mem_read.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_void_p,
                                   ctypes.c_size_t]
        uc.uc_mem_map.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_size_t,
                                  ctypes.c_uint32]
        uc.uc_emu_start.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64,
                                    ctypes.c_uint64, ctypes.c_size_t]
        uc.uc_ctl.argtypes = [ctypes.c_void_p, ctypes.c_int]
        h = self.h = ctypes.c_void_p()
        assert uc.uc_open(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, ctypes.byref(h)) == 0
        assert uc.uc_ctl(h, UC_CTL_CPU_MODEL | (1 << 26) | (1 << 30),
                         ctypes.c_int(cpu)) == 0
        assert uc.uc_mem_map(h, 0, MEM, 7) == 0

    def write(self, addr, data):
        assert self.uc.uc_mem_write(self.h, addr, bytes(data), len(data)) == 0

    def read(self, addr, n):
        buf = ctypes.create_string_buffer(n)
        assert self.uc.uc_mem_read(self.h, addr, buf, n) == 0
        return buf.raw

    def reg(self, r, v):
        x = ctypes.c_uint32(v)
        self.uc.uc_reg_write(self.h, r, ctypes.byref(x))

    def regs(self):
        """d0-d7, a0-a7"""
        out = []
        for i in range(16):
            x = ctypes.c_uint32()
            self.uc.uc_reg_read(self.h, (REG_D0 if i < 8 else REG_A0) + i % 8, ctypes.byref(x))
            out.append(x.value)
        return out

    def call(self, target, regs, until=None):
        """Call target with regs (d0-d7, a0-a7) until it returns, or from target to until."""
        self.write(STUB, b'\x4e\xb9' + target.to_bytes(4, 'big')
                   + b'\x4e\xf9' + SENTINEL.to_bytes(4, 'big'))
        self.reg(REG_SR, 0x2700)
        for i, v in enumerate(regs):
            self.reg((REG_D0 if i < 8 else REG_A0) + i % 8, v)
        begin, end = (STUB, SENTINEL) if until is None else (target, until)
        err = self.uc.uc_emu_start(self.h, begin, end, 0, 0)
        if err:
            pc = ctypes.c_uint32()
            self.uc.uc_reg_read(self.h, REG_PC, ctypes.byref(pc))
            raise RuntimeError(f'emulation error {err} at pc {pc.value:#x}')


def main():
    cases = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    rnd = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    code, new = hunk(2), assemble()
    fast = slow = 0
    for n in range(cases):
        w = 16 * rnd.randrange(1, 21)
        x0 = 16 * rnd.randrange(0, (320 - w) // 16 + 1)
        rows = rnd.choice([1, 2, 126, rnd.randrange(1, 201)])
        y0 = rnd.randrange(0, 200 - rows + 1)
        stride = rnd.choice([320, 336, x0 + w + 16 * rnd.randrange(0, 4)])
        layout = rnd.choice(['game', 'apart'])
        p4, p6 = (P2 + 2 * BPL, P2 + 4 * BPL) if layout == 'game' else (P4, P6)
        chunky = rnd.randbytes(stride * (rows + 2) + 64)
        planes = [rnd.randbytes(size) for _, size in AREAS]
        off = y0 * ROWLEN + x0 // 8
        regs = [rnd.getrandbits(32) for _ in range(16)]
        regs[6] = (regs[6] & 0xffff0000) | (w // 16 - 1)
        regs[7] = (regs[7] & 0xffff0000) | (rows - 1)
        regs[8] = CHUNKY + x0
        regs[11:15] = [P0 + off, P2 + off, p4 + off, p6 + off]
        regs[15] = STACK
        out = []
        for target in (LOOP, CODE_NEW):
            m = Machine()
            m.write(0, code)
            m.write(MODC, struct.pack('>hh', stride - w, ROWLEN - w // 8))
            m.write(CODE_NEW, new)
            m.write(CHUNKY, chunky)
            for (a, _), data in zip(AREAS, planes):
                m.write(a, data)
            m.call(target, regs)
            out.append([m.read(a, size) for a, size in AREAS])
        if out[0] == planes:
            sys.exit(f'case {n}: the planes did not change')
        if out[0] != out[1]:
            for (a, _), x, y in zip(AREAS, *out):
                for i in range(len(x)):
                    if x[i] != y[i]:
                        print(f'case {n}: w {w} x0 {x0} rows {rows} y0 {y0} stride {stride} '
                              f'{layout}: first difference at {a + i:#x}: START {x[i]:02x}, '
                              f'new {y[i]:02x}')
                        sys.exit(1)
        if w % 32:
            slow += 1
        else:
            fast += 1
    print(f'{cases} cases identical ({fast} converted by _c2p030, {slow} by START\'s loop)')


if __name__ == '__main__':
    main()
