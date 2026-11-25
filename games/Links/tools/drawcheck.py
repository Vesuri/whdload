#!/usr/bin/env python3
"""Differential check of the slave's course drawing routines against v1.53's (golf hunk 12).

    python3 tools/drawcheck.py [N]

Loads tmp/game/Links/data/golf's hunks (relocated, each at 0x100000 + 0x10000 x hunk) and
the slave's routines (assembled from src/Links_WHD.s) into Unicorn's 68020, and runs both
on N random cases each (default 2000), from random flags:

- the span loop (hunk 12 $5E2-$60A, its set-up's 8 values written into the code) against
  _span1 (the values in _sp1): every register and the memory around a1;
- the pixel loop (hunk 12 $74E-$796, the add/sub bits in its opcodes) against _span2 (the
  bits in _sp2): every register and the three buffers;
- N / 100 pictures (hunk 12 $AF2, hunk 4's 64 plane routines; its pointers in hunk 12
  $BA6, hunk 0 $60C and $610, hunk 19 $1AC, the colour table hunk 46 $C2C) against
  _copyscr with its tables from _c2pinit: the six planes (and the picture, regions and
  map unchanged).
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
UC_ARCH_M68K, UC_MODE_BIG_ENDIAN = 7, 1 << 30
UC_CTL_CPU_MODEL, UC_CPU_M68K_M68020 = 7, 2
REG_A0, REG_D0, REG_SR, REG_PC = 1, 9, 17, 18
MEM = 0x800000
HUNKS = 0x100000                    # hunk i at HUNKS + 0x10000 * i
CODE_NEW = 0x600000
BUF, PLANES, PIC, REG, MAP, C2P = 0x640000, 0x680000, 0x690000, 0x6A0000, 0x6B0000, 0x6E0000
STACK, SENTINEL = 0x7E0000, 0x7F0000


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


def hunks(path):
    """The code/data hunks' bytes, relocated to HUNKS + 0x10000 x hunk."""
    d = path.read_bytes()
    u = lambda p: struct.unpack_from('>I', d, p)[0]
    assert u(0) == 0x3F3
    p = 4
    while u(p):
        p += 4 + 4 * u(p)
    p += 4
    first, last = u(p + 4), u(p + 8)
    p += 12 + 4 * (last - first + 1)
    out, cur = [], None
    while p < len(d):
        t = u(p) & 0x3FFFFFFF
        p += 4
        if t in (0x3E9, 0x3EA):
            n = u(p) * 4
            cur = bytearray(d[p + 4:p + 4 + n])
            out.append(cur)
            p += 4 + n
        elif t == 0x3EB:
            cur = bytearray(u(p) * 4)
            out.append(cur)
            p += 4
        elif t == 0x3EC:
            while True:
                c = u(p)
                p += 4
                if not c:
                    break
                h = u(p)
                p += 4
                for k in range(c):
                    o = u(p + 4 * k)
                    struct.pack_into('>I', cur, o, (struct.unpack_from('>I', cur, o)[0]
                                                    + HUNKS + 0x10000 * h) & 0xFFFFFFFF)
                p += 4 * c
        elif t == 0x3F2:
            pass
        else:
            raise ValueError(f'hunk type {t:#x}')
    assert all(len(h) <= 0x10000 for h in out)
    return out


def assemble():
    """_span1, _span2, _copyscr and _c2pinit at CODE_NEW: branches at 0, 4, 8 and 12, then
    the addresses of C2PBUF, _sp1 and _sp2."""
    src = (ROOT / 'src/Links_WHD.s').read_text(encoding='latin-1')
    start = src.index("; v1.53's span loop (hunk 12 $5e2")
    end = src.index('\trts\n', src.index('\n_c2pinit\n')) + 5
    text = (f'\tORG\t${CODE_NEW:x}\n\tbra.w\t_span1\n\tbra.w\t_span2\n\tbra.w\t_copyscr\n'
            f'\tbra.w\t_c2pinit\n\tdc.l\tC2PBUF,_sp1,_sp2\n'
            f'{src[start:end]}\nC2PBUF\tdc.l\t0\n')
    (ROOT / 'tmp').mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'draw.s', tmp / 'draw.bin'
    s.write_text(text, encoding='latin-1')
    vasm = os.environ.get('VASM', 'vasmm68k_mot')
    try:
        subprocess.run([vasm, '-m68000', '-devpac', '-Fbin', '-quiet', '-o', str(b), str(s)],
                       check=True)
        data = b.read_bytes()
    finally:
        for p in tmp.iterdir():
            p.unlink()
        tmp.rmdir()
    return data, struct.unpack_from('>3I', data, 16)


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

    def call(self, pc, regs, until=SENTINEL, ret=None, ccr=0):
        """Runs from pc until `until` with regs (d0-d7, a0-a6); the stack holds SENTINEL, and
        under it `ret` (the jsr's return) if given. Returns d0-d7, a0-a7 and the flags."""
        self.reg(REG_SR, 0x2700 | ccr)
        sp = STACK - 4
        self.write(sp, SENTINEL.to_bytes(4, 'big'))
        if ret is not None:
            sp -= 4
            self.write(sp, ret.to_bytes(4, 'big'))
        for i in range(8):
            self.reg(REG_D0 + i, regs[i])
        for i in range(7):
            self.reg(REG_A0 + i, regs[8 + i])
        self.reg(REG_A0 + 7, sp)
        err = self.uc.uc_emu_start(self.h, pc, until, 0, 50_000_000)
        if err or self.reg(REG_PC) != until:
            raise RuntimeError(f'emulation error {err} at pc {self.reg(REG_PC):#x} from {pc:#x}')
        # Not the flags: read at the stop they are not reliable (one case gave Z clear after
        # a beq that was taken); both versions end on the loop's own subq.
        return [self.reg(REG_D0 + i) for i in range(8)] + [self.reg(REG_A0 + i) for i in range(8)]


def r32(rng):
    return rng.choice((0, 0xFFFFFFFF, 0x10000, 0xFFFF, rng.randrange(1 << 32), rng.randrange(1 << 32)))


def span1(m, h12, sp1, rng):
    # the set-up's two branches (hunk 12 $502, $52c) and its three signs ($562-$5c8)
    if rng.random() < 0.5:
        first, disp, op5f0 = 0x4E71, 0, 0x93
    else:
        first, disp, op5f0 = 0x5240, 6, 0xD3
    signs = [rng.choice((0x90, 0xD0)) | k for k in (0, 2, 4)]
    vals = {0x5E2: first.to_bytes(2, 'big'), 0x5E6: disp.to_bytes(2, 'big'),
            0x5EA: (disp + 2).to_bytes(2, 'big'), 0x5EE: (disp + 4).to_bytes(2, 'big'),
            0x5F0: bytes([op5f0]), 0x5FC: bytes([signs[0]]), 0x5FE: bytes([signs[1]]),
            0x600: bytes([signs[2]])}
    d3 = rng.choice((1, 1, 2, 2, 3, rng.randrange(1, 64), rng.randrange(1, 400)))
    a1 = BUF + 0x8000 + rng.randrange(0, 16, 2)
    regs = [r32(rng) for _ in range(8)] + [0xA0A0A0A0, a1, 0xA2A2A2A2, 0xA3A3A3A3, 0xA4A4A4A4,
                                            0xA5A5A5A5, 0xA6A6A6A6]
    regs[3] = (regs[3] & 0xFFFF0000) | d3
    ccr = rng.randrange(32)
    fill = rng.randbytes(0x10000)
    out = []
    for new in (False, True):
        m.write(BUF, fill)
        for o, v in vals.items():
            m.write((sp1 + o - 0x5E2) if new else (h12 + o), v)
        if new:
            out.append(m.call(CODE_NEW, regs, h12 + 0x60C, ret=h12 + 0x5E2, ccr=ccr))
        else:
            out.append(m.call(h12 + 0x5E2, regs, h12 + 0x60C, ccr=ccr))
        out[-1].append(m.read(BUF, 0x10000))
    return out


def span2(m, h12, sp2, rng):
    bits = [rng.choice((0x92, 0xD2)), rng.choice((0x90, 0xD0))]  # $78a (d6,d1), $790 (d7,d0)
    d2 = rng.choice((1, 1, 2, 3, rng.randrange(1, 40), rng.randrange(1, 320)))
    rec = struct.pack('>HHH', rng.randrange(320), rng.randrange(65536), rng.randrange(65536))
    a4 = rng.randrange(0, 0x400)
    bda = rng.randrange(65536)
    regs = [r32(rng) for _ in range(8)] + [BUF, MAP, 0xA2A2A2A2, PIC, a4, REG, PLANES + 0x8000]
    regs[2] = (regs[2] & 0xFFFF0000) | d2
    ccr = rng.randrange(32)
    fills = [rng.randbytes(0x4000) for _ in range(3)] + [rng.randbytes(0x10000)]
    out = []
    for new in (False, True):
        m.write(BUF, rec)
        m.write(MAP, fills[0] * 2)
        m.write(PIC, fills[1])
        m.write(REG, fills[2])
        m.write(PLANES, fills[3])
        m.write(h12 + 0xBDA, bda.to_bytes(2, 'big'))
        if new:
            m.write(h12 + 0x78A, b'\xd2')
            m.write(h12 + 0x790, b'\xd0')
            m.write(sp2, bytes([bits[0] & 0x40, bits[1] & 0x40]))
            out.append(m.call(CODE_NEW + 4, regs, h12 + 0x798, ret=h12 + 0x74E, ccr=ccr))
        else:
            m.write(h12 + 0x78A, bytes([bits[0]]))
            m.write(h12 + 0x790, bytes([bits[1]]))
            out.append(m.call(h12 + 0x74E, regs, h12 + 0x798, ccr=ccr))
        out[-1].append(m.read(MAP, 0x8000) + m.read(PIC, 0x4000) + m.read(REG, 0x4000))
    return out


def picture(m, h12, c2pbuf, rng):
    # the colour and dither table (hunk 46 $C2C, built by the game): colours 0-63 (hunk 4
    # has 64 routines), for picture bytes 0-127 and dither steps 0-3
    table = bytes(rng.randrange(64) for _ in range(512))
    m.write(HUNKS + 0x10000 * 46 + 0xC2C, table)
    good = range(128)
    n = 51200
    kinds = rng.random()
    pic = bytearray(n)
    regions = bytearray(n)
    region = 0
    for i in range(n):
        if rng.random() < 0.02:
            region = rng.randrange(64)
        regions[i] = region
        pic[i] = rng.choice(good) if rng.random() > kinds * 0.5 else (256 - rng.randrange(1, 64))
    depth = b''.join(struct.pack('>H', 0xFFFF if rng.random() < 0.3 else rng.randrange(65535))
                     for _ in range(n + 1))
    screen = rng.randbytes(48000)
    d0 = rng.choice((0, 0, 0, rng.randrange(160)))
    d4 = rng.choice((0, 1, 2, 3))
    regs = [d0, 0, 0, 0, d4, 0, 0, 0] + [0] * 7
    out = []
    for new in (False, True):
        m.write(PLANES, screen)
        m.write(PIC, pic)
        m.write(REG, regions)
        m.write(MAP, depth)
        for (hunk, off), v in (((12, 0xBA6), MAP + 2), ((0, 0x60C), PLANES + 8000),
                               ((19, 0x1AC), PIC), ((0, 0x610), REG)):
            m.write(HUNKS + 0x10000 * hunk + off, v.to_bytes(4, 'big'))
        if new:
            m.write(c2pbuf, C2P.to_bytes(4, 'big'))
            m.call(CODE_NEW + 8, regs, ret=h12 + 0xAF8)
        else:
            m.call(h12 + 0xAF2, regs)
        out.append((m.read(PLANES, 48000), m.read(PIC, n), m.read(REG, n), m.read(MAP, 2 * n + 2)))
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    golf = ROOT / 'tmp/game/Links/data/golf'
    hs = hunks(golf)
    code, (c2pbuf, sp1, sp2) = assemble()
    m = Machine(load_unicorn())
    for i, h in enumerate(hs):
        m.write(HUNKS + 0x10000 * i, h)
    m.write(CODE_NEW, code)
    h12 = HUNKS + 0x10000 * 12
    m.write(C2P, bytes(4096))
    m.call(CODE_NEW + 12, [0] * 8 + [C2P] + [0] * 6)        # _c2pinit
    rng = random.Random(1)
    fails = 0
    for name, fn, count in (('span loop', lambda: span1(m, h12, sp1, rng), n),
                            ('pixel loop', lambda: span2(m, h12, sp2, rng), n),
                            ('picture', lambda: picture(m, h12, c2pbuf, rng),
                             max(1, n // 100))):
        bad = 0
        for k in range(count):
            a, b = fn()
            if a != b:
                bad += 1
                if bad <= 3:
                    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
                    print(f'{name} case {k}: differs in {diff}',
                          [(a[i], b[i]) for i in diff if not isinstance(a[i], bytes)])
        print(f'{name}: {count - bad}/{count} equal')
        fails += bad
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
