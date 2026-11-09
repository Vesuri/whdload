#!/usr/bin/env python3
"""Enhanced framerate routine checks: BH's own code with timing.s's patches, in Unicorn.

  python3 tools/timing_check.py [--cpu 68000|68040] [SLAVE [LISTING]]

Loads BH (Disk.1, `make unpack`) relocated into an isolated CPU-only memory, applies the
slave's _pl_timing list as resload_PatchSeg would (default: the release build, `make
build BUILD=release`, symbols from its listing), and runs single game routines at T 4, 7,
25 and 50 against exact values, the original routines beside them:
- stick: bh:7920 (dt_stick), the roll and pitch rates from a stick over T steps sum to
  stick x steps / mission T (the original divided by the live T and truncated);
- turn: bh:79fe (dt_turn), heading and pitch-change rates sum to v sin(roll)/4, v cos(roll);
- mouse limit: bh:3eb0, in flight the per-frame limit 191/127 x mission T / T (at most
  255), outside a flight the original's;
- object step: bh:827e..86b0 for a class-1 object (dt_steplen, dt_polar): one game second
  (T steps) moves it the same distance at every T;
- AI turn: bh:11e18..11f48 (dt_aiadd/dt_aisub): one game second turns the heading by
  a k / (3 x 65536) at every T, a the folded bank, k = 19584(a4)[object].
No emulator services, timing or interrupts are modelled.  Run from the game directory.
"""
import argparse, ctypes as C, math, os, re, struct, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _amigaxdev  # noqa: F401,E402
from amigaxdev.patchlist import decode, slave_code  # noqa: E402
import xmatch  # noqa: E402

u = C.CDLL(str(Path(os.environ.get('AMIGA_UNICORN', '~/.local/share/amiga/unicorn')).expanduser()
               / 'lib/libunicorn.2.dylib'))
P, I, Q, Z = C.c_void_p, C.c_int, C.c_uint64, C.c_size_t
for n, args in {'uc_open': [I, I, C.POINTER(P)], 'uc_ctl': [P, C.c_uint32],
                'uc_mem_map': [P, Q, Q, C.c_uint32], 'uc_mem_write': [P, Q, P, Z],
                'uc_mem_read': [P, Q, P, Z], 'uc_reg_write': [P, I, P], 'uc_reg_read': [P, I, P],
                'uc_emu_start': [P, Q, Q, Q, Z], 'uc_close': [P]}.items():
    getattr(u, n).argtypes = args
    getattr(u, n).restype = I
u.uc_strerror.argtypes = [I]
u.uc_strerror.restype = C.c_char_p
A4, A5, A7, D0, D4, SR, PC = 5, 6, 8, 9, 13, 17, 18      # Unicorn m68k register ids
CODE, DATA, BSS, SLAVE, BUF, STACK = 0x100000, 0x200000, 0x220000, 0x400000, 0x500000, 0x6f0000
STOP = 0x1000
DATA_ALLOC = 0xF1EC             # BH's data hunk allocation (docs/profiling.md §1)


class CPU:
    def ck(self, e):
        if e:
            raise RuntimeError(u.uc_strerror(e).decode())

    def __init__(self, model):
        self.h = P()
        self.ck(u.uc_open(7, 1 << 30, C.byref(self.h)))           # UC_ARCH_M68K, big endian
        self.ck(u.uc_ctl(self.h, 7 | (1 << 26) | (1 << 30), C.c_int(model)))
        self.ck(u.uc_mem_map(self.h, 0, 0x800000, 7))

    def write(self, a, b):
        self.ck(u.uc_mem_write(self.h, a, b, len(b)))

    def read(self, a, n):
        b = C.create_string_buffer(n)
        self.ck(u.uc_mem_read(self.h, a, b, n))
        return b.raw

    def reg(self, r, v=None):
        x = C.c_uint32(0 if v is None else v & 0xffffffff)
        self.ck(u.uc_reg_read(self.h, r, C.byref(x)) if v is None
                else u.uc_reg_write(self.h, r, C.byref(x)))
        return x.value

    def flush(self):
        self.ck(u.uc_ctl(self.h, 9 | (2 << 26) | (1 << 30), Q(0), Q(0x800000)))

    def run(self, pc, until):
        self.reg(SR, 0x2700)                 # before A7: a mode change swaps stack pointers
        self.reg(A7, STACK)
        self.write(STACK, struct.pack('>I', STOP))
        e = u.uc_emu_start(self.h, pc, until, 0, 2000000)
        if e:
            raise RuntimeError(f'{u.uc_strerror(e).decode()} at bh:{self.reg(PC) - CODE:x}')
        if self.reg(PC) != until:
            raise RuntimeError(f'stopped at {self.reg(PC):#x}, not {until:#x}')


class BH:
    def __init__(self, model, slave, listing, patched):
        self.c = c = CPU(model)
        h = xmatch.hunks(xmatch.bh_exe())
        bases = [CODE, DATA, BSS]
        mem = [bytearray(h[0][1]), bytearray(h[1][1]) + bytes(DATA_ALLOC - len(h[1][1])), bytearray(4)]
        for i in range(2):
            for tgt, offs in h[i][2].items():
                for o in offs:
                    v = struct.unpack_from('>I', mem[i], o)[0] + bases[tgt]
                    struct.pack_into('>I', mem[i], o, v)
        self.orig_code = bytes(mem[0])
        for b, m in zip(bases, mem):
            c.write(b, bytes(m))
        self.a4 = DATA + 0x7ffe
        c.reg(A4, self.a4)
        code = slave_code(slave)
        c.write(SLAVE, code)
        self.syms = {m[1]: int(m[0], 16) for m in
                     re.findall(r'^([0-9A-F]{8}) (\S+)$', Path(listing).read_text(encoding='latin1'), re.M)}
        self.lput('dt_buf', BUF, 'I')
        self.lput('dt_bh', CODE, 'I')
        self.lput('dt_hz', 50)
        if patched:
            for adr, cmd, arg in decode(code, self.syms['_pl_timing']):
                if cmd == 'END':
                    break
                if cmd in ('P', 'PS'):
                    dest = SLAVE + int(arg.split(':')[1], 16)
                    c.write(CODE + adr, (b'\x4e\xf9' if cmd == 'P' else b'\x4e\xb9') + struct.pack('>I', dest))
                elif cmd == 'NOP':
                    c.write(CODE + adr, b'\x4e\x71' * (int(arg, 16) // 2))
                else:
                    raise SystemExit(f'timing_check: PL_{cmd} not handled')
        c.flush()

    def lput(self, name, v, fmt='h'):
        self.c.write(SLAVE + self.syms[name], struct.pack('>' + fmt, v))

    def set(self, off, v, fmt='h'):
        if fmt in 'hl' and v >= 1 << (8 * struct.calcsize('>' + fmt) - 1):
            fmt = fmt.upper()
        self.c.write(self.a4 + off, struct.pack('>' + fmt, v))

    def get(self, off, fmt='h'):
        return struct.unpack('>' + fmt, self.c.read(self.a4 + off, struct.calcsize('>' + fmt)))[0]

    def run(self, start, end):
        self.c.reg(A4, self.a4)
        self.c.run(CODE + start, CODE + end)

    def timing(self, t, tm):
        self.set(10184, t)
        self.set(10186, t // 8 + 1)
        self.lput('dt_tm', tm)
        self.lput('dt_flying', -1)
        self.c.write(BUF, bytes(0x1000))


TS = (4, 7, 25, 50)
failures = []


def check(ok, msg):
    print(('ok    ' if ok else 'FAIL  ') + msg)
    if not ok:
        failures.append(msg)


def stick(fixed, orig):
    print('# stick: per-step rates summed over T steps (one game second), mission T 7')
    for s10308, s10310 in ((384, -2112), (-10240, 1536), (128, 12288)):
        for t in TS:
            sums = {}
            for name, bh in (('fixed', fixed), ('orig', orig)):
                bh.timing(t, 7)
                r = [0, 0]
                for _ in range(t):
                    bh.set(10308, s10308)
                    bh.set(10310, s10310)
                    bh.run(0x7920, 0x7982)
                    r[0] += bh.get(28506)
                    r[1] += bh.get(28508)
                sums[name] = r
            exact = [abs(s10308) * t / 7 * (1 if s10308 >= 0 else -1),
                     abs(s10310) * t / 7 * (1 if s10310 >= 0 else -1)]
            ok = all(abs(f - e) <= 1 for f, e in zip(sums['fixed'], exact))
            check(ok, f'stick {s10308:6d},{s10310:6d} T {t:2d}: fixed {sums["fixed"]}, '
                      f'exact {[round(e, 1) for e in exact]}, original {sums["orig"]}')


def turn(fixed):
    print('# turn: heading and pitch-change rates over T steps from v = pitch stick / mission T')
    sin = lambda a: struct.unpack('>H', fixed.c.read(fixed.a4 + 670 + ((a & 0xffff) >> 5 & ~1), 2))[0]
    for s10310, roll in ((-2112, 0x1800), (1536, 0xe000), (384, 0x5000)):
        for t in TS:
            fixed.timing(t, 7)
            h = p = 0
            for _ in range(t):
                fixed.set(10308, 0)
                fixed.set(10310, s10310)
                fixed.set(15240, roll)
                fixed.run(0x7920, 0x7982)
                fixed.run(0x79fe, 0x7a24)
                h += fixed.get(28510)
                p += fixed.get(28512)
            v = s10310 * t / 7
            sgn = lambda a: -1 if a & 0x8000 else 1
            eh = v * sin(roll) / 65536 * sgn(roll) / 4
            ep = v * sin(roll + 0x4000) / 65536 * sgn(roll + 0x4000)
            check(abs(h - eh) <= 1.5 and abs(p - ep) <= 1.5,
                  f'turn stick {s10310:6d} roll {roll:#06x} T {t:2d}: heading {h} '
                  f'(exact {eh:.1f}), pitch {p} (exact {ep:.1f})')


def mouse(fixed):
    print('# mouse limit per frame, mission T 7')
    for t in TS:
        fixed.timing(t, 7)
        fixed.set(10298, 500)
        fixed.set(10300, -500)
        fixed.run(0x3eb0, 0x3ee8)
        lx = min(255, (191 * 7 + t // 2) // t)
        ly = min(255, (127 * 7 + t // 2) // t)
        x, y = fixed.get(10298), fixed.get(10300)
        check((x, y) == (lx, -ly), f'mouse T {t:2d}: {x},{y} (expected {lx},{-ly})')
    fixed.lput('dt_flying', 0)
    fixed.set(10298, 500)
    fixed.set(10300, -500)
    fixed.run(0x3eb0, 0x3ee8)
    x, y = fixed.get(10298), fixed.get(10300)
    check((x, y) == (191, -127), f'mouse outside a flight: {x},{y} (expected the original 191,-127)')


def objstep(fixed, orig):
    print('# object step: a class-1 object over one game second (T steps)')
    obj = 5
    for speed, heading, pitch in ((156, 0x2345, 0x0400), (40, 0xc000, 0xfc00), (327, 0x7ff0, 0x0000)):
        res = {}
        for name, bh in (('fixed', fixed), ('orig', orig)):
            res[name] = {}
            for t in TS:
                bh.timing(t, 7)
                bh.set(10452 + obj, 1, 'B')
                bh.set(10596 + obj, 1, 'B')
                bh.set(15696 + 2 * obj, speed)
                bh.set(14328 + 2 * obj, heading)
                bh.set(14616 + 2 * obj, pitch)
                pos0 = (60000000, 60000000, 300000)
                for k, off in enumerate((10908, 11484, 12060)):
                    bh.set(off + 4 * obj, pos0[k], 'l')
                for _ in range(t):
                    bh.c.reg(D4, obj)
                    bh.c.reg(A5, STACK - 0x100)
                    bh.run(0x827e, 0x86b0)
                res[name][t] = tuple(bh.get(off + 4 * obj, 'l') - p0
                                     for off, p0 in zip((10908, 11484, 12060), pos0))
        ref = res['fixed'][7]
        length = math.sqrt(sum(x * x for x in ref))
        for t in TS:
            f, o = res['fixed'][t], res['orig'][t]
            err = max(abs(a - b) for a, b in zip(f, ref))
            oerr = max(abs(a - b) for a, b in zip(o, res['orig'][7]))
            check(err <= max(3, length * 0.001),
                  f'object speed {speed:3d} T {t:2d}: moved {f} ({err} from T 7; original {o}, {oerr} off)')


def aiturn(fixed, orig):
    print('# AI turn: heading change over one game second (T steps)')
    obj = 9
    for roll, k in ((0xf000, 9000), (0x1200, 23000), (0xc400, 4000)):
        res = {}
        for name, bh in (('fixed', fixed), ('orig', orig)):
            res[name] = {}
            for t in TS:
                bh.timing(t, 7)
                bh.set(15240 + 2 * obj, roll)
                bh.set(19584 + 2 * obj, k)
                bh.set(14328 + 2 * obj, 0)
                bh.set(14904 + obj, 0, 'B')
                for _ in range(t):
                    bh.c.reg(D4, obj)
                    bh.c.reg(A5, STACK - 0x100)
                    bh.run(0x11e18, 0x11f48)
                h = bh.get(14328 + 2 * obj)
                res[name][t] = h
        a = (-roll) & 0xffff
        if a & 0x8000:
            a = (-a) & 0xffff
            sign = -1
        else:
            sign = 1
        if a > 16384:
            a = 32768 - a
        exact = sign * a * k / (3 * 65536)
        for t in TS:
            f, o = res['fixed'][t], res['orig'][t]
            check(abs(f - exact) <= 1, f'AI roll {roll:#06x} k {k:5d} T {t:2d}: heading {f:+d} '
                                       f'(exact {exact:+.1f}; original {o:+d})')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--cpu', default='68000', choices=('68000', '68040'))
    p.add_argument('slave', nargs='?', default='tmp/build/release/Battlehawks1942.Slave')
    p.add_argument('listing', nargs='?')
    a = p.parse_args()
    listing = a.listing or str(Path(a.slave).with_suffix('.lst'))
    model = 1 if a.cpu == '68000' else 4
    fixed = BH(model, a.slave, listing, True)
    orig = BH(model, a.slave, listing, False)
    print(f'# Unicorn {a.cpu}')
    stick(fixed, orig)
    turn(fixed)
    mouse(fixed)
    objstep(fixed, orig)
    aiturn(fixed, orig)
    print(f'# {len(failures)} failed' if failures else '# all passed')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
