#!/usr/bin/env python3
"""Differential check of the slave's span drawer (SpanD) and far rows (FarRow) against the game's.

    python3 tools/spancheck.py [N]

Runs the game's span drawer (SPS 627 `$11E52`, SPS 628 `$1210A`, from the program file in
tmp/game) and the slave's (assembled from src/ArchipelagosFiles_WHD.s) in Unicorn's 68020 on
N random rows each (default 3000): a span list as draw view builds it (ends rising to 255,
some zero-width, some at 0 before the first), a random map with objects, a random screen,
random object variables. Compares the three planes, the map, the body from `$12800` (the
variables and lists), a0, a2, a6 and the stack pointer. And N random far rows: the game's
loop (`$11E0E`, `$120C6`) and FarRow from the same steps, accumulators, x and cell, each
to the list end (`$11E2C`, `$120E4`); compares the list, its end (a5), the cell (d4), a0,
a2 and the stack pointer. And N / 10 random gaps between two rows (GapFill): every object
whose cell's centre lies between them (a cell in from the rays) and on neither row is
noted, nothing else is, each once, the map keeps all but those bits 7, a0, a2, a3, a5, a6 and
the stack pointer are kept (the span drawer follows and takes no others), and nothing is noted beyond the object limit or with the list full. The program sits at address 0, so
its relocated longs (the fill table) are the file's offsets.
"""
import ctypes
import math
import os
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UC_ARCH_M68K, UC_MODE_BIG_ENDIAN = 7, 1 << 30
UC_CTL_CPU_MODEL, UC_CPU_M68K_M68020 = 7, 2
REG_A0, REG_D0, REG_SR, REG_PC = 1, 9, 17, 18
MEM = 0x800000
CODE_NEW, SENTINEL, STACK = 0x700000, 0x7F0000, 0x7E0000
MAP, SCREEN = 0x70000, 0x5C780
VERSIONS = {  # drawer, span list, row, object limit, object list length, object list,
    # the cell steps, the far rows' loop and its end, the row records
    'Archipelagos': (0x11E52, 0x13C26, 0x12890, 0x12892, 0x1288E, 0x12F26, 0x129BA, 0x11E0E,
                     0x11E2C, 0x12FA6),
    'ArchipelagosNTSC': (0x1210A, 0x13FCA, 0x12C34, 0x12C36, 0x12C32, 0x132CA, 0x12D5E,
                         0x120C6, 0x120E4, 0x1334A),
}
GFMAX = 96   # the list bytes GapFill fills to


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


def assemble():
    """SpanD and FarRow with their tables, and GameBody (0), at CODE_NEW: at 0 and 4 a
    branch to each, at 8 GameBody, at 12 the addresses of SD627, SD628 and SDVer."""
    src = (ROOT / 'src/ArchipelagosFiles_WHD.s').read_text(encoding='latin-1')
    start = src.index('SD627\tdc.l')
    end = src.index('; The pre-scaler (the title')
    text = (f'\t\tORG\t${CODE_NEW:x}\n\t\tbra.w\tSpanD\n\t\tbra.w\tFarRow\n'
            f'GameBody\tdc.l\t0\n\t\tdc.l\tSD627,SD628,SDVer\n\t\tbra.w\tGapFill\n'
            f'{src[start:end]}\n')
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'span.s', tmp / 'span.bin'
    s.write_text(text, encoding='latin-1')
    vasm = os.environ.get('VASM', 'vasmm68k_mot')
    try:
        subprocess.run([vasm, '-m68020', '-devpac', '-Fbin', '-quiet', '-o', str(b), str(s)],
                       check=True)
        data = b.read_bytes()
    finally:
        for p in tmp.iterdir():
            p.unlink()
        tmp.rmdir()
    sd627, sd628, sdver = struct.unpack_from('>3I', data, 12)
    return data, {'SpanD': CODE_NEW, 'FarRow': CODE_NEW + 4, 'SD627': sd627, 'SD628': sd628,
                  'SDVer': sdver, 'GapFill': CODE_NEW + 24}


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

    def call(self, pc, regs, until=SENTINEL):
        self.reg(REG_SR, 0x2700)
        sp = STACK - 4
        self.write(sp, SENTINEL.to_bytes(4, 'big'))
        for i in range(8):
            self.reg(REG_D0 + i, regs[i])
        for i in range(7):
            self.reg(REG_A0 + i, regs[8 + i])
        self.reg(REG_A0 + 7, sp)
        err = self.uc.uc_emu_start(self.h, pc, until, 0, 2_000_000)
        if err or self.reg(REG_PC) != until:
            raise RuntimeError(f'emulation error {err} at pc {self.reg(REG_PC):#x} from {pc:#x}')
        return [self.reg(REG_D0 + i) for i in range(8)] + [self.reg(REG_A0 + i) for i in range(8)]


def case(rng, v):
    """A row: (list entries, map, screen, variables, row offset)."""
    entries = [(0, rng.randrange(-32768, 32768)) for _ in range(rng.choice((0, 0, 1, 2)))]
    x = 0
    for _ in range(rng.randrange(0, 24)):
        x = min(255, x + rng.choice((0, 1, 2, 3, 7, 15, 16, 17, 31, 32, 33, 40, 64)))
        if x == 0:
            x = 1
        entries.append((x, rng.randrange(-32768, 32768)))
    entries.append((255, rng.randrange(-32768, 32768)))
    if rng.random() < 0.1:
        entries.append((255, rng.randrange(-32768, 32768)))
    world = bytes(b & (0xFF if b % 3 == 0 else 0x7F) for b in rng.randbytes(256))
    row = rng.randrange(67)
    var = (rng.randrange(0, 135, 2), rng.randrange(0, 135), rng.randrange(0, 40, 2))
    return entries, world, row, var


SCREENS = [random.Random(i).randbytes(24000) for i in range(8)]


def run(m, v, entries, world, row, var, drawer, new):
    m.write(MAP, (world * 256)[:0x10000])
    m.write(SCREEN, SCREENS[row % len(SCREENS)])
    lst = b''.join(struct.pack('>Hh', x, c) for x, c in entries)
    m.write(v[1], lst + b'\xAA\xAA' * 8)
    m.write(v[2], struct.pack('>H', var[0]))
    m.write(v[3], struct.pack('>H', var[1]))
    m.write(v[4], struct.pack('>H', var[2]))
    m.write(v[5], bytes(128))
    a6 = SCREEN + 7204 - 40 * (row + 1)
    a5 = v[1] + len(lst)           # the list's end: the drawer writes its 0 there
    regs = [0x11111111 * (i + 1) for i in range(8)] + [
        0x1254A if v[0] == 0x11E52 else 0x128EE, 0xA1A1A1A1,
        0x1258A if v[0] == 0x11E52 else 0x1292E, 0x78000, a6, a5, a6]
    out = m.call(new if new else drawer, regs)
    return (m.read(SCREEN, 24000), m.read(MAP, 0x10000), m.read(0x12800, 0x1800),
            out[8], out[10], out[14], out[15])


def far_case(rng):
    """A far row: d0, d1 (the steps), d6, d5 (the accumulators), d2 (x), d4 (the cell),
    the x step (a byte) and the y step (a word)."""
    step = lambda: rng.choice((1, 2, 3, rng.randrange(1, 256), rng.randrange(1, 32769),
                               rng.randrange(1, 65536), 32768))
    return (step(), step(), rng.randrange(65536), rng.randrange(65536),
            rng.choice((0, 255, rng.randrange(256))), rng.randrange(65536),
            rng.choice((1, 0xFF, rng.randrange(256))), rng.choice((0x100, 0xFF00, rng.randrange(65536))))


def far_run(m, v, c, pc):
    d0, d1, d6, d5, d2, d4, sx, sy = c
    m.write(v[1], bytes(4 * 300))
    m.write(v[6], bytes([sx, 0]) + struct.pack('>H', sy))
    regs = [d0 | 0xABCD0000, d1 | 0x12340000, d2, 0x33333333, d4 | 0x56780000, d5 | 0x9ABC0000,
            d6 | 0xDEF00000, 0x77777777, 0xA0A0A0A0, 0xA1A1A1A1, 0xA2A2A2A2, 0x78000, 0xA4A4A4A4,
            v[1], 0xA6A6A6A6]
    out = m.call(pc, regs, v[8])
    return m.read(v[1], 4 * 300), out[13], out[4] & 0xFFFF, out[8], out[10], out[15]


def gap_case(rng):
    """Two rows' records as draw view makes them: a position, a heading, the rays at
    +-32 degrees, the nearer row's depth and the farther's (cells); the row, the limit,
    the list's length; a map with objects in about one cell in six."""
    px, py = rng.randrange(65536), rng.randrange(65536)
    th = rng.uniform(0, 2 * math.pi)
    da = rng.uniform(1, 50)
    db = da + rng.choice((rng.uniform(0, 1), rng.uniform(1, 3), rng.uniform(3, 6)))
    recs = []
    for d in (da, db):
        rx = px + d * 256 * math.cos(th - math.radians(32))
        ry = py + d * 256 * math.sin(th - math.radians(32))
        lx = px + d * 256 * math.cos(th + math.radians(32))
        ly = py + d * 256 * math.sin(th + math.radians(32))
        recs.append((int(rx), int(ry), int(lx) - int(rx), int(ly) - int(ry)))
    row = rng.randrange(2, 135, 2)
    limit = rng.choice((126, 126, 126, rng.randrange(0, 135, 2)))
    length = rng.choice((0, 0, rng.randrange(0, 80, 2)))
    world = bytes(b | 0x80 if rng.random() < 0.16 else b & 0x7F for b in rng.randbytes(0x10000))
    return recs, row, limit, length, world


def cell(x, y):
    return ((int(y) >> 8 & 255) << 8) | (int(x) >> 8 & 255)


def addr(c):
    return 0x78000 + (c - 0x10000 if c & 0x8000 else c)


def gap_run(m, v, recs, row, limit, length, world):
    """GapFill on a case: (registers kept, the cells it noted, the map's other changes,
    the cells it should have noted, why not checked)."""
    m.write(MAP, world)
    m.write(v[2], struct.pack('>H', row))
    m.write(v[3], struct.pack('>H', limit))
    m.write(v[4], struct.pack('>H', length))
    m.write(v[5], bytes(128))
    m.write(v[9] + 4 * (row - 2), b''.join(struct.pack('>HHhh', x & 0xFFFF, y & 0xFFFF,
                                                       dx, dy) for x, y, dx, dy in recs))
    regs = [0x11111111 * (i + 1) for i in range(7)] + [row] + [
        0xA0A0A0A0, 0xA1A1A1A1, 0xA2A2A2A2, 0x78000, 0xA4A4A4A4, 0xA5A5A5A5, 0xA6A6A6A6]
    out = m.call(m.gap, regs)
    kept = [out[i] for i in (8, 10, 11, 13, 14, 15)] == [regs[i] for i in (8, 10, 11, 13, 14)] + [STACK]
    n = struct.unpack('>H', m.read(v[4], 2))[0]
    got = [struct.unpack_from('>H', m.read(v[5], 128), i)[0] for i in range(length, n, 2)]
    after = m.read(MAP, 0x10000)
    changed = {i for i in range(0x10000) if after[i] != world[i]}
    noted = {addr(c) - MAP for c in got}
    wrong = changed ^ noted or any(after[i] != world[i] & 0x7F for i in noted)
    if row > limit:
        return kept, got, wrong, set(), 'off'
    (ax, ay, adx, ady), (bx, by, bdx, bdy) = recs
    quad = [(ax, ay), (ax + adx, ay + ady), (bx + bdx, by + bdy), (bx, by)]
    rows = set()
    for x, y, dx, dy in recs:
        steps = int((abs(dx) + abs(dy)) / 4) + 2
        rows |= {cell(x + dx * t / steps, y + dy * t / steps) for t in range(steps + 1)}
    want = set()
    for c in cells_in(quad):
        if world[addr(c) - MAP] & 0x80 and c not in rows:
            want.add(c)
    if n >= GFMAX:
        return kept, got, wrong, want, 'full'
    return kept, got, wrong, want, ''


def cells_in(quad):
    """The cells whose centre lies in the quadrilateral (8.8 corners, convex), at least
    a cell from its sides (the rays) and 1/32 of one from its ends (the rows)."""
    xs = [x for x, _ in quad]
    ys = [y for _, y in quad]
    edges = [(quad[i], quad[(i + 1) % 4]) for i in range(4)]
    for cy in range(int(min(ys)) >> 8, (int(max(ys)) >> 8) + 1):
        for cx in range(int(min(xs)) >> 8, (int(max(xs)) >> 8) + 1):
            x, y = cx * 256 + 128, cy * 256 + 128
            ok = True
            for k, ((x0, y0), (x1, y1)) in enumerate(edges):
                if (x0, y0) == (x1, y1):
                    continue
                d = ((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0)) / math.hypot(x1 - x0, y1 - y0)
                if -d < (8 if k % 2 == 0 else 256):
                    ok = False
                    break
            if ok:
                yield ((cy & 255) << 8) | (cx & 255)


def main(args):
    n = int(args[0]) if args else 3000
    uc = load_unicorn()
    code, syms = assemble()
    bad = 0
    for name, v in VERSIONS.items():
        body = (ROOT / f'tmp/game/{name}/data/Archipelagos_03FC00').read_bytes()[0x1C:]
        orig, new = Machine(uc), Machine(uc)
        for m in (orig, new):
            m.write(0, body)
        new.write(CODE_NEW, code)
        new.write(syms['SDVer'], syms['SD627' if name == 'Archipelagos' else 'SD628'].to_bytes(4, 'big'))
        rng = random.Random(1)
        diff = 0
        for i in range(n):
            c = case(rng, v)
            a = run(orig, v, *c, v[0], None)
            b = run(new, v, *c, v[0], syms['SpanD'])
            if a != b:
                diff += 1
                if diff <= 3:
                    what = [k for k, x, y in zip(('screen', 'map', 'vars', 'a0', 'a2', 'a6', 'sp'),
                                                  a, b) if x != y]
                    print(f'{name} case {i}: differs in {", ".join(what)}; entries {c[0]}')
        print(f'{name}: {n} rows, {diff} differ')
        bad += diff
        diff = 0
        for i in range(n):
            c = far_case(rng)
            a = far_run(orig, v, c, v[7])
            b = far_run(new, v, c, syms['FarRow'])
            if a != b:
                diff += 1
                if diff <= 3:
                    what = [k for k, x, y in zip(('list', 'a5', 'd4', 'a0', 'a2', 'sp'), a, b) if x != y]
                    print(f'{name} far case {i}: differs in {", ".join(what)}; {c}')
        print(f'{name}: {n} far rows, {diff} differ')
        bad += diff
        new.gap = syms['GapFill']
        diff = full = noted = 0
        for i in range(n // 10):
            c = gap_case(rng)
            kept, got, wrong, want, why = gap_run(new, v, *c)
            full += why == 'full'
            noted += len(got)
            miss = want - set(got) if not why else set()
            if not kept or wrong or len(set(got)) != len(got) or miss \
                    or (why == 'off' and got):
                diff += 1
                if diff <= 3:
                    print(f'{name} gap case {i}: kept {kept}, map wrong {bool(wrong)}, '
                          f'{len(got)} noted, missed {sorted(miss)[:8]}, {why}')
        print(f'{name}: {n // 10} gaps ({full} with the list full), {noted} objects noted, '
              f'{diff} wrong')
        bad += diff
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main(sys.argv[1:])
