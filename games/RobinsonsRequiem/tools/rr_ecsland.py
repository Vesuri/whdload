#!/usr/bin/env python3
"""The ECS game's landscape, original against patched, from snapshots: rr_ecsland.py SNAPDIR

For each tools/rr_snap.py snapshot in SNAPDIR (the machine at hunk 1 +$bee2, the landscape's
entry, once per frame): loads chip and fast memory into Unicorn (68000), runs the landscape
until it returns (the address on the stack) once as the game has it and once with the
slave's landscape patches (PATCHES: src/ files assembled at CODE, the sites rewritten as
the slave does), and compares all memory but the stack below the entry's stack pointer
(and the patch sites, put back first), and the registers at the return. The snapshots carry the slave of the build that took them
(its sky copy, its conversion): the landscape calls the sky copy, which jumps into it.
With PATCHES empty (as committed: no landscape patch is kept) it runs the original only and
reports the bytes it changed, a check of the snapshots; a patch under test goes into PATCHES
and SOURCES. Exit status 1 on the first difference. The snapshots are game bytes: keep them
in tmp/.
"""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rr_c2pcheck import REG_A0, REG_D0, REG_PC, REG_SR, Machine, UC_CPU_M68K_M68000  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAND = 0xbee2
CODE = 0x600000             # the patch code (unmapped on the A500 machine)
STACK_SLACK = 0x4000        # the stack below the entry's pointer: scratch, not compared
# The landscape patches: (hunk 1 offset, the routine it jumps to, jsr or jmp); src files.
PATCHES = []
SOURCES = []


def assemble(h1):
    if not SOURCES:
        return b'', {}
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b, lst = tmp / 'land.s', tmp / 'land.bin', tmp / 'land.lst'
    s.write_text(f'\t\tORG\t${CODE:x}\n_hunk1\tdc.l\t${h1:x}\n'
                 + ''.join(f'\t\tINCLUDE\t"{ROOT / "src" / f}"\n' for f in SOURCES))
    subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), '-m68000', '-devpac', '-Fbin',
                    '-quiet', '-L', str(lst), '-o', str(b), str(s)], check=True)
    data = b.read_bytes()
    syms = {}
    for line in lst.read_text(encoding='latin1').splitlines():
        f = line.split()
        if len(f) == 2 and f[1].startswith('A:'):     # absolute (ORG): A:<address>
            syms[f[0]] = int(f[1][2:], 16) - CODE
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return data, syms


class Land(Machine):
    def __init__(self, snap, info):
        super().__init__(UC_CPU_M68K_M68000)
        uc, h = self.uc, self.h
        for a, size in ((0xbf0000, 0x10000),   # 0-$7fffff: Machine
                        (0xdf0000, 0x10000), (0xf80000, 0x80000)):
            assert uc.uc_mem_map(h, a, size, 7) == 0
        p = 0
        for a, b in info['regions']:
            self.write(a, snap[p:p + b - a])
            p += b - a
        if int(info['regions'][0][1]) > 0x100000:
            raise ValueError('regions')

    def setregs(self, regs):
        names = ['d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7',
                 'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'fp', 'sp']
        self.reg(REG_SR, regs['ps'])     # first: it picks the stack pointer A7 is
        for i, n in enumerate(names):
            self.reg((REG_D0 if i < 8 else REG_A0) + i % 8, regs[n])

    def run(self, begin, until):
        err = self.uc.uc_emu_start(self.h, begin, until, 0, 0)
        pc = ctypes.c_uint32()
        self.uc.uc_reg_read(self.h, REG_PC, ctypes.byref(pc))
        if err or pc.value != until:
            raise RuntimeError(f'emulation error {err} at pc {pc.value:#x}')


def run_one(snap, info, patched):
    regs = info['regs']
    h1 = int(info['hunks'][1], 16)
    m = Land(snap, info)
    original = m.read(h1, 0xea30)
    if patched:
        code, syms = assemble(h1)
        m.write(CODE, code)
        for off, label, op in PATCHES:
            m.write(h1 + off, bytes.fromhex({'jsr': '4eb9', 'jmp': '4ef9'}[op])
                    + (CODE + syms[label]).to_bytes(4, 'big'))
    m.setregs(regs)
    sp = regs['sp']
    ret = int.from_bytes(m.read(sp, 4), 'big')
    m.run(h1 + LAND, ret)
    for off, _, _ in PATCHES if patched else ():     # the sites back as the game has them
        m.write(h1 + off, original[off:off + 6])
    mem = [m.read(a, b - a) for a, b in info['regions']]
    lo = sp - STACK_SLACK - info['regions'][1][0]
    hi = sp - info['regions'][1][0]
    if 0 <= lo and hi <= len(mem[1]):
        mem[1] = mem[1][:lo] + bytes(hi - lo) + mem[1][hi:]
    return mem, m.regs()


def main():
    d = Path(sys.argv[1])
    snaps = sorted(d.glob('snap-*.json'))
    if not snaps:
        sys.exit(f'no snapshots in {d}')
    for j in snaps:
        info = json.loads(j.read_text())
        snap = j.with_suffix('.bin').read_bytes()
        a, ra = run_one(snap, info, False)
        changed = sum(x != y for x, y in zip(b''.join(a), snap))
        if not PATCHES:
            print(f'{j.stem}: the landscape ran, {changed} bytes changed')
            continue
        b, rb = run_one(snap, info, True)
        if a != b or ra[:15] != rb[:15]:
            for (base, _), x, y in zip(info['regions'], a, b):
                diff = [i for i in range(len(x)) if x[i] != y[i]]
                if diff:
                    print(f'{j.stem}: {len(diff)} bytes differ, first at {base + diff[0]:#x}')
            if ra[:15] != rb[:15]:
                print(f'{j.stem}: registers {[hex(x) for x in ra[:15]]} '
                      f'against {[hex(x) for x in rb[:15]]}')
            sys.exit(1)
        print(f'{j.stem}: identical ({changed} bytes changed by the landscape)')


if __name__ == '__main__':
    main()
