#!/usr/bin/env python3
"""Differential check of the slave's EdgeStep against the game's edge scan converter.

    python3 tools/edgecheck.py [N]

Runs the game's stepping code (program offsets $14BE..$165B, from tmp/game/Sentinel/Disk.1,
self-modification and all), the slave's EdgeStep and EdgeStepF (the fast drawing option's,
with its tables elsewhere: its tables are compared with the game's) (assembled from
src/Sentinel.s) in
Unicorn's 68000 on N random edges (default 20000): both tables, both x directions, x-major
and y-major, clipped and not, rows 0 to 255 (0 wraps to 256), random registers. Compares
d0-d7, a0-a7, N, Z, V and C and the low 64 KB (the edge tables at $7B00/$7D00 and the
variables). The game's code runs at its own address, BASE $57FE4.

The return address holds `move.w sr,(SRSAVE).l`: Unicorn's own SR read gives stale flags. X
is only counted: the game's `subq.w #1,d1` sets it on a borrow, EdgeStep's `add.w` of -1 on a
carry, and no instruction in the routine reads it, nor do its three callers before setting it
($1370, $173A, $1796).
"""
import ctypes
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UC_ARCH_M68K, UC_MODE_BIG_ENDIAN = 7, 1 << 30
UC_CTL_CPU_MODEL, UC_CPU_M68K_M68000, UC_CPU_M68K_M68020 = 7, 1, 2
REG_A0, REG_D0, REG_SR, REG_PC = 1, 9, 17, 18
BASE, OLD = 0x57fe4, 0x57fe4 + 0x14be
MEM = 0x200000
CODE_NEW, RET, STACK = 0x100000, 0x1F0000, 0x1E0000
SENTINEL, SRSAVE = RET + 6, RET + 0x100
LOW = 0x10000


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
    uc.uc_ctl.argtypes = [ctypes.c_void_p, ctypes.c_int]
    return uc


def program():
    """The program as the slave loads it: the image's first nine tracks, 9 of 10 sectors each."""
    disk = (ROOT / 'tmp/game/Sentinel/Disk.1').read_bytes()
    return b''.join(disk[t * 5120:t * 5120 + 4608] for t in range(9))


def assemble():
    src = (ROOT / 'src/Sentinel.s').read_text(encoding='latin-1')
    start, end = src.index('\nEDGESTEP\tMACRO\n'), src.index('\nCheckKeys\n')
    text = f'\tORG\t${CODE_NEW:x}\n{src[start:end]}\n\tdc.l\tEdgeStepF,edgedelta\n'
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'edge.s', tmp / 'edge.bin'
    s.write_text(text, encoding='latin-1')
    try:
        subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), '-m68000', '-devpac', '-Fbin',
                        '-quiet', '-o', str(b), str(s)], check=True)
        return b.read_bytes()
    finally:
        for p in tmp.iterdir():
            p.unlink()
        tmp.rmdir()


class Machine:
    def __init__(self, uc, prog, new, model=UC_CPU_M68K_M68000):
        self.uc = uc
        h = ctypes.c_void_p()
        assert uc.uc_open(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, ctypes.byref(h)) == 0
        self.h = h
        assert uc.uc_ctl(h, UC_CTL_CPU_MODEL | (1 << 26) | (1 << 30),
                         ctypes.c_int(model)) == 0
        assert uc.uc_mem_map(h, 0, MEM, 7) == 0
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
        err = self.uc.uc_emu_start(self.h, pc, SENTINEL, 0, 5_000_000)
        if err or self.reg(REG_PC) != SENTINEL:
            raise RuntimeError(f'emulation error {err} at pc {self.reg(REG_PC):#x} from {pc:#x}')
        return ([self.reg(REG_D0 + i) for i in range(8)] + [self.reg(REG_A0 + i) for i in range(8)]
                + [int.from_bytes(self.read(SRSAVE, 2), 'big') & 0x1f])


def case(rng):
    """Low memory (variables set) and the registers for one edge."""
    low = bytearray(rng.randbytes(LOW))
    def w(a, v):
        low[a:a + 2] = (v & 0xffff).to_bytes(2, 'big')
    w(0x18dc, rng.choice((0x7b00, 0x7d00, 0x7b00, 0x7d00, 0x7c00)))
    big = rng.random() < 0.1
    x0 = rng.randrange(-2000, 2400) if big else rng.randrange(-40, 360)
    x1 = x0 + (rng.randrange(-3000, 3000) if big else rng.choice(
        (0, 1, -1, rng.randrange(-300, 300), rng.randrange(-40, 40))))
    w(0x18e8, x0)
    w(0x18ec, x1)
    w(0x18de, rng.choice((0, 1, 2, rng.randrange(256), rng.randrange(256), rng.randrange(65536)
                          if big else rng.randrange(200))))
    low[0x18ea] = rng.choice((0, 0, 0, 1, 0x80, rng.randrange(256)))
    low[0x18eb] = rng.choice((0, 1, rng.randrange(256), rng.randrange(1, 193), rng.randrange(1, 193)))
    regs = [rng.getrandbits(32) for _ in range(15)]
    regs[8 + 6] = rng.getrandbits(32)
    return bytes(low), regs, rng.randrange(32)


FAST_TABLES = 0x17b00     # EdgeStepF's tables in the check: edgedelta $10000
TABLES = range(0x7b00, 0x7f00)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    uc = load_unicorn()
    prog, new = program(), assemble()
    fast_pc, delta_at = (int.from_bytes(new[-8 + 4 * i:len(new) - 4 + 4 * i], 'big') for i in range(2))
    old_m, new_m = Machine(uc, prog, new), Machine(uc, prog, new)
    fast_m = Machine(uc, prog, new, UC_CPU_M68K_M68020)    # EdgeStepF runs on a 68020 or up
    fast_m.write(delta_at, (FAST_TABLES - 0x7b00).to_bytes(4, 'big'))
    rng = random.Random(1)
    bad = xdiff = 0
    paths = {}
    for i in range(n):
        low, regs, ccr = case(rng)
        out = []
        for m, pc in ((old_m, OLD), (new_m, CODE_NEW), (fast_m, fast_pc)):
            m.write(0, low)
            m.write(FAST_TABLES, low[TABLES.start:TABLES.stop])
            r = m.call(pc, regs, ccr)
            mem = m.read(0, LOW)
            if m is fast_m:          # its tables in place of the game's
                mem = mem[:TABLES.start] + m.read(FAST_TABLES, len(TABLES)) + mem[TABLES.stop:]
            out.append((r, mem))
        dx = int.from_bytes(low[0x18ec:0x18ee], 'big', signed=True) - \
            int.from_bytes(low[0x18e8:0x18ea], 'big', signed=True)
        key = ('x' if abs(dx) >= int.from_bytes(low[0x18de:0x18e0], 'big') else 'y',
               'clip' if low[0x18ea] else 'plain', '+' if dx < 0 else '-')
        paths[key] = paths.get(key, 0) + 1
        if any(o[0][16] & 0x10 != out[0][0][16] & 0x10 for o in out[1:]):
            xdiff += 1
        out = [([*r[:16], r[16] & 0x0f], mem) for r, mem in out]
        if out[0] != out[1] or out[0] != out[2]:
            bad += 1
            if bad <= 5:
                (ro, mo), (rn, mn) = out[0], (out[1] if out[0] != out[1] else out[2])
                diff = [j for j in range(LOW) if mo[j] != mn[j]]
                names = [f'd{j}' for j in range(8)] + [f'a{j}' for j in range(8)] + ['ccr']
                print(f'case {i} {key}: regs differ {[(names[j], hex(ro[j]), hex(rn[j])) for j in range(17) if ro[j] != rn[j]]}'
                      f' memory differs at {[hex(a) for a in diff[:8]]}{"..." if len(diff) > 8 else ""}')
    print(f'{n} edges (EdgeStep and EdgeStepF), paths {dict(sorted(paths.items()))}: '
          f'{bad} differ ({xdiff} in X only)')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
