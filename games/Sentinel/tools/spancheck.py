#!/usr/bin/env python3
"""Differential check of the slave's SpanFill against the game's span filler.

    python3 tools/spancheck.py [N]

Runs the game's span filler (program offsets $18B4..$1B17, from tmp/game/Sentinel/Disk.1,
with its tables at $55000 as the game loads them) and the slave's SpanFill (assembled from
src/Sentinel.s, after SpanTables has checked those tables) in Unicorn's 68020 on N random
polygons (default 3000): random edges and rows (spans inside, across and outside the
window, rows whose right edge is left of their left edge, overflowing words), the game's
clip windows (320 pixels from 0, 112 from 64, 128 from 0, a multiple of 8 from 0) and some
it never sets, colours, both row tables ($18BA 0 and 800) and both strip halves ($195A 0 and
80), over random picture bytes. Compares the picture ($70000..$80FFF), the low 64 KB but for
$191A..$191D (the game's scratch for one row, which every reader writes first), d1, d2, a1,
a2 and N, Z, V, C. The game's code runs at its own address, BASE $57FE4.
"""
import ctypes
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from edgecheck import (ROOT, BASE, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_CTL_CPU_MODEL,  # noqa: E402
                       REG_A0, REG_D0, REG_SR, REG_PC, load_unicorn, program)

UC_CPU_M68K_M68020 = 2
OLD = BASE + 0x18b4
MEM = 0x200000
CODE_NEW, RET, STACK = 0x100000, 0x1F0000, 0x1E0000
SENTINEL, SRSAVE = RET + 6, RET + 0x100
LOW = 0x10000
PIC, PIC_END = 0x70000, 0x81000
SCRATCH = range(0x191a, 0x191e)
WINDOWS = ((0, 320), (64, 112), (0, 128))


def tables():
    """The data the game copies to $55000..$56FFF: the image from track 11, 8 KB."""
    disk = (ROOT / 'tmp/game/Sentinel/Disk.1').read_bytes()
    return disk[9 * 5120:9 * 5120 + 8192]


def assemble():
    src = (ROOT / 'src/Sentinel.s').read_text(encoding='latin-1')
    group = src[src.index('\nGROUP\tMACRO'):src.index('\tENDM', src.index('\nGROUP\tMACRO')) + 6]
    start = src.index('\tMACHINE\t68020\nSpanTables\n')
    end = src.index("; The pan step's column for a horizontal step")
    text = (f'\tORG\t${CODE_NEW:x}\nBASE\t= ${BASE:x}\n{group}\n'
            f'\tjmp\tSpanFill\n\tjmp\tSpanTables\n\tdc.l\tspanok\n{src[start:end]}\n')
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'span.s', tmp / 'span.bin'
    s.write_text(text, encoding='latin-1')
    try:
        subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), '-m68020', '-devpac', '-Fbin',
                        '-quiet', '-nomsg=2051', '-o', str(b), str(s)], check=True)
        return b.read_bytes()
    finally:
        for p in tmp.iterdir():
            p.unlink()
        tmp.rmdir()


class Machine:
    def __init__(self, uc, prog, data, new):
        self.uc = uc
        h = ctypes.c_void_p()
        assert uc.uc_open(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, ctypes.byref(h)) == 0
        self.h = h
        assert uc.uc_ctl(h, UC_CTL_CPU_MODEL | (1 << 26) | (1 << 30),
                         ctypes.c_int(UC_CPU_M68K_M68020)) == 0
        assert uc.uc_mem_map(h, 0, MEM, 7) == 0
        self.write(0x55000, data)
        self.write(BASE, prog)
        self.write(CODE_NEW, new)
        self.write(RET, bytes.fromhex('40f9') + SRSAVE.to_bytes(4, 'big'))

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

    def call(self, pc, regs, ccr):
        self.reg(REG_SR, 0x2700 | ccr)
        sp = STACK - 4
        self.write(sp, RET.to_bytes(4, 'big'))
        for i in range(8):
            self.reg(REG_D0 + i, regs[i])
        for i in range(7):
            self.reg(REG_A0 + i, regs[8 + i])
        self.reg(REG_A0 + 7, sp)
        err = self.uc.uc_emu_start(self.h, pc, SENTINEL, 0, 20_000_000)
        if err or self.reg(REG_PC) != SENTINEL:
            raise RuntimeError(f'emulation error {err} at pc {self.reg(REG_PC):#x} from {pc:#x}')
        return ([self.reg(REG_D0 + i) for i in range(8)] + [self.reg(REG_A0 + i) for i in range(8)]
                + [int.from_bytes(self.read(SRSAVE, 2), 'big') & 0x1f])


def case(rng):
    """Low memory (variables and edge tables set), the picture and the registers."""
    low = bytearray(rng.randbytes(LOW))
    def w(a, v):
        low[a:a + 2] = (v & 0xffff).to_bytes(2, 'big')
    left, width = rng.choice(WINDOWS + ((0, 8 * rng.randrange(1, 32)),))
    if rng.random() < 0.05:          # windows the game never sets: SpanFill leaves them to it
        left, width = rng.randrange(0, 80), rng.randrange(0, 330)
    w(0x18f0, left)
    w(0x18f2, width)
    w(0x18f4, left + width if rng.random() < 0.97 else rng.randrange(65536))
    tab = rng.choice((0, 800))
    w(0x18ba, tab)
    low[0x195a:0x195e] = rng.choice((0, 0, 80)).to_bytes(4, 'big')
    low[0x1693] = rng.randrange(256)
    low[0x17f0] = rng.randrange(256) & (0xff if rng.random() < 0.05 else 0x7f)
    # rows: the table holds 200 rows of each buffer from index ($ef - top)
    n = rng.choice((1, 2, rng.randrange(1, 40), rng.randrange(1, 200)))
    r0 = rng.randrange(0, 201 - n)
    top = 0xef - r0
    bottom = top - n + 1
    if rng.random() < 0.03:
        bottom = (top + rng.randrange(1, 20)) & 0xff
    low[0x1680], low[0x167e] = top & 0xff, bottom & 0xff
    big = rng.random() < 0.05
    x = rng.randrange(-60, 340)
    wd = rng.randrange(0, 200)
    for y in range(256):
        if big:
            lv, rv = rng.randrange(65536), rng.randrange(65536)
        else:
            x += rng.randrange(-6, 7)
            wd += rng.randrange(-5, 6)
            lv, rv = x, x + (wd if rng.random() > 0.02 else -rng.randrange(1, 9))
            if rng.random() < 0.05:
                lv, rv = rng.randrange(-400, 700), rng.randrange(-400, 700)
        w(0x7b00 + 2 * y, lv)
        w(0x7d00 + 2 * y, rv)
    regs = [rng.getrandbits(32) for _ in range(15)]
    return bytes(low), rng.randbytes(PIC_END - PIC), regs, rng.randrange(32)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    uc = load_unicorn()
    prog, data, new = program(), tables(), assemble()
    old_m, new_m = Machine(uc, prog, data, new), Machine(uc, prog, data, new)
    new_m.call(CODE_NEW + 6, [0] * 15, 0)            # SpanTables
    flag = int.from_bytes(new_m.read(CODE_NEW + 12, 4), 'big')
    if new_m.read(flag, 1) != b'\xff':
        print('SpanTables: the tables are not the plain ones')
        return 1
    rng = random.Random(1)
    bad = fast = drawn = 0
    for i in range(n):
        low, pic, regs, ccr = case(rng)
        word = lambda a: int.from_bytes(low[a:a + 2], 'big')
        if not (low[0x17f0] & 0x80 or word(0x18f0) & 7 or word(0x18f2) & 7
                or (word(0x18f0) + word(0x18f2)) & 0xffff != word(0x18f4)):
            fast += 1
        out = []
        for m, pc in ((old_m, OLD), (new_m, CODE_NEW)):
            m.write(0, low)
            m.write(PIC, pic)
            r = m.call(pc, regs, ccr)
            mem = bytearray(m.read(0, LOW))
            for a in SCRATCH:
                mem[a] = 0
            out.append(([r[1], r[2], r[9], r[10], r[16] & 0x0f], bytes(mem), m.read(PIC, PIC_END - PIC)))
        drawn += out[0][2] != pic
        if out[0] != out[1]:
            bad += 1
            if bad <= 5:
                (ro, lo, po), (rn, ln, pn) = out
                dl = [hex(a) for a in range(LOW) if lo[a] != ln[a]][:6]
                dp = [hex(PIC + a) for a in range(len(po)) if po[a] != pn[a]][:6]
                print(f'case {i}: regs {ro} {rn} low {dl} picture {dp}')
    print(f'{n} polygons ({fast} on SpanFill\'s own path, {drawn} drawing): {bad} differ')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
