#!/usr/bin/env python3
"""FR2 host check: run the assembled FastRenderBlit.s under Unicorn (68020/68040)
on every oracle case and compare with tools/fr2_model.py, scratch and end state.

  fr2_unicorn.py [CPU] [--limit N]      CPU 68020 (default) or 68040

Not the FR2 gate (the gate is the in-guest hardware oracle); a fast way to find
asm bugs before booting the emulator.
"""
import ctypes, os, re, struct, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fr2_cases import REC, FRB, xorshift_fill, run_model
from fr2_model import Mem

R = Path(__file__).resolve().parents[1]
GAMES = R / 'src'
U = ctypes.CDLL(str(Path(os.environ.get('AMIGA_UNICORN', Path.home() / '.local/share/amiga/unicorn')) / 'lib/libunicorn.2.dylib'))
U.uc_ctl.argtypes = [ctypes.c_void_p, ctypes.c_int]
CODE, IMAGE, STACK, SCR = 0x1000, 0x40000, 0x80000, 0x100000
REG = {f'a{i}': 1 + i for i in range(8)} | {f'd{i}': 9 + i for i in range(8)} | {'sr': 17, 'pc': 18}


def build():
    d = R / 'tmp/build/fr2-unicorn'; d.mkdir(parents=True, exist_ok=True)
    (d / 'wrap.s').write_text(' org $1000\nFRK_COUNT equ 1\nwrap_blit:\n bsr.w FastRenderBlit\nwrap_blit_end:\n nop\n'
                              'wrap_bdat:\n bsr.w FastRenderBDAT\nwrap_bdat_end:\n nop\n include "FastRenderBlit.s"\n')
    vasm = os.environ.get('VASM', str(Path.home() / '.local/vasmm68k_mot'))
    subprocess.run([vasm, '-m68020', '-Fbin', '-quiet', f'-I{GAMES}', '-L', 'wrap.list', '-o', 'wrap.bin', 'wrap.s'], cwd=d, check=True)
    sy = {n: int(v, 16) for v, n in re.findall(r'^([0-9A-F]{8}) (\w+)$', (d / 'wrap.list').read_text(errors='replace'), re.M)}
    return (d / 'wrap.bin').read_bytes(), sy


class UC:
    def __init__(self, cpu):
        self.h = ctypes.c_void_p()
        assert U.uc_open(7, 1 << 30, ctypes.byref(self.h)) == 0
        model = {'68020': 2, '68030': 3, '68040': 4}[cpu]
        assert U.uc_ctl(self.h, 7 | 1 << 26 | 1 << 30, ctypes.c_int(model)) == 0
        for a, n in ((0, 0x100000), (SCR, 0x20000)):
            assert U.uc_mem_map(self.h, ctypes.c_uint64(a), ctypes.c_size_t(n), 7) == 0

    def w(self, a, data):
        assert U.uc_mem_write(self.h, ctypes.c_uint64(a), data, ctypes.c_size_t(len(data))) == 0

    def r(self, a, n):
        b = ctypes.create_string_buffer(n)
        assert U.uc_mem_read(self.h, ctypes.c_uint64(a), b, ctypes.c_size_t(n)) == 0
        return b.raw

    def reg(self, name, v=None):
        x = ctypes.c_uint32(0 if v is None else v & 0xffffffff)
        if v is None:
            U.uc_reg_read(self.h, REG[name], ctypes.byref(x)); return x.value
        U.uc_reg_write(self.h, REG[name], ctypes.byref(x))

    def call(self, start, end):
        self.reg('sr', 0x2700); self.reg('a7', STACK)
        rc = U.uc_emu_start(self.h, ctypes.c_uint64(start), ctypes.c_uint64(end), ctypes.c_uint64(0), ctypes.c_size_t(0))
        assert rc == 0, rc
        assert self.reg('pc') == end, hex(self.reg('pc'))


def image_state(img):
    g = lambda off, n=2: struct.unpack_from('>H' if n == 2 else '>I', img, off)[0]
    return dict(con0=g(0), con1=g(2), cpt=g(8, 4), bpt=g(12, 4), apt=g(16, 4), dpt=g(20, 4),
                cdat=g(0x30), bdat=g(0x32), adat=g(0x34), bold=g(0x36), bhold=g(0x38))


def main(cpu='68020', limit=None):
    code, sy = build()
    uc = UC(cpu); uc.w(CODE, code)
    blob = (R / 'tmp/build/fr2-data/FR2Cases.bin').read_bytes()
    n = len(blob) // REC if limit is None else min(limit, len(blob) // REC)
    bad = []; import collections; hits = collections.Counter()
    for i in range(n):
        rec = blob[i * REC:(i + 1) * REC]
        size2, reloc, seed, ln, pattern, kind = struct.unpack_from('>HHIIHH', rec, 0x3c)
        img = bytearray(rec[:0x3c])
        for bit, off in enumerate((0x10, 0x0c, 0x08, 0x14)):
            if reloc >> bit & 1:
                struct.pack_into('>I', img, off, struct.unpack_from('>I', img, off)[0] + SCR)
        data = xorshift_fill(ln, seed, pattern)
        # Reference.
        g = lambda off: struct.unpack_from('>H', img, off)[0]
        regs = {k: (struct.unpack_from('>I', img, o)[0] if k in ('cpt', 'bpt', 'apt', 'dpt') else g(o)) for k, o in FRB.items()}
        mem = bytearray(data)
        mb, rc = run_model(regs, regs['size'], size2, Mem(mem, SCR))
        # Unicorn: BDAT write with B history cleared (the oracle's primer blit), then the blit(s).
        struct.pack_into('>HH', img, 0x36, 0, 0)
        uc.w(SCR, bytes(data)); uc.w(IMAGE, bytes(img))
        uc.reg('a0', IMAGE); uc.reg('d0', g(0x32)); uc.call(sy['wrap_bdat'], sy['wrap_bdat_end'])
        h0 = struct.unpack('>I', uc.r(sy['FRKHits'], 4))[0] if 'FRKHits' in sy else 0
        uc.reg('a0', IMAGE); uc.call(sy['wrap_blit'], sy['wrap_blit_end']); rc1 = uc.reg('d0')
        if 'FRKHits' in sy and struct.unpack('>I', uc.r(sy['FRKHits'], 4))[0] != h0:
            hits[(kind, '%04x' % (regs['con0'] & 0xfff), regs['con1'] & 0x1a)] += 1
        if size2:
            uc.w(IMAGE + 0x18, struct.pack('>H', size2))
            uc.reg('a0', IMAGE); uc.call(sy['wrap_blit'], sy['wrap_blit_end'])
        got = uc.r(SCR, ln); st = image_state(uc.r(IMAGE, 0x3c))
        want = dict(con0=mb.con0, con1=mb.con1, cpt=mb.cpt, bpt=mb.bpt, apt=mb.apt, dpt=mb.dpt, cdat=mb.cdat,
                    bdat=mb.bdat, adat=mb.adat, bold=mb.bold, bhold=mb.bhold)
        diff = [k for k in want if (want[k] & 0xffffffff) != st[k]]
        if got != bytes(mem[:ln]) or diff or rc1 != rc:
            first = next((j for j in range(ln) if got[j] != mem[j]), None)
            bad.append(dict(index=i, kind=kind, con0=hex(regs['con0']), con1=hex(regs['con1']), size=hex(regs['size']),
                            size2=size2, first=first, state={k: (hex(want[k]), hex(st[k])) for k in diff}, rc=(rc, rc1)))
    print(cpu, 'cases', n, 'mismatches', len(bad), 'kernel cases', sum(hits.values()))
    if '-v' in sys.argv:
        for k, v in sorted(hits.items()): print(' hit', k, v)
    for b in bad[:12]:
        print(b)
    return bad


if __name__ == '__main__':
    a = sys.argv[1:]
    lim = int(a[a.index('--limit') + 1]) if '--limit' in a else None
    cpu = next((x for x in a if x.startswith('680')), '68020')
    sys.exit(1 if main(cpu, lim) else 0)
