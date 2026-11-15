#!/usr/bin/env python3
"""The landscape, original against patched, from snapshots: rr_land.py SNAPDIR

For each tools/rr_snap.py snapshot in SNAPDIR (the machine at the landscape's entry, hunk 1
+$d88c in the AGA game and +$bee2 in the ECS one, once per frame): loads chip and fast
memory into Unicorn (a 68030 for the AGA game, a 68000 for the ECS one), runs the landscape
until it returns (the address on the stack) once as the game has it and once with the
slave's landscape patches (PATCHES: src/ files assembled at CODE, the sites rewritten as
the slave does), and compares all memory but the stack below the entry's stack pointer
(and the patch sites, put back first), and the registers at the return. The snapshots carry the slave of the build that took them
(the ECS game's sky copy, the AGA game's map rows and copies): the landscape calls into it.
With no patches for the variant it runs the original only and reports the bytes it
changed, a check of the snapshots; a patch under test goes into PATCHES and SOURCES. Exit status 1 on the first difference. The snapshots are game bytes: keep them
in tmp/.
"""
import ctypes
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rr_c2pcheck import REG_A0, REG_D0, REG_PC, REG_SR, Machine, UC_CPU_M68K_M68000  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
UC_CPU_M68K_M68030 = 3
# by variant: the landscape's entry, hunk 1's size, the CPU, the address for the patch
# code (outside the machine's memory)
LAND = {'RobinsonsRequiemAGA': 0xd88c, 'RobinsonsRequiem': 0xbee2}
H1SIZE = {'RobinsonsRequiemAGA': 0x103d8, 'RobinsonsRequiem': 0xea30}
CPU = {'RobinsonsRequiemAGA': UC_CPU_M68K_M68030, 'RobinsonsRequiem': UC_CPU_M68K_M68000}
CODE = {'RobinsonsRequiemAGA': 0xa00000, 'RobinsonsRequiem': 0x600000}
STACK_SLACK = 0x4000        # the stack below the entry's pointer: scratch, not compared
# The landscape patches, by variant: (hunk 1 offset, the routine it jumps to, jsr or jmp);
# the src files that hold them; an installer the slave runs instead (its label, run with a0
# hunk 1, a1 a 16-byte aligned block for its copies, and d0 non-zero when it patched, and
# the sites it writes: (hunk 1 offset, bytes)).
PATCHES = {'RobinsonsRequiemAGA': [], 'RobinsonsRequiem': []}
SOURCES = {'RobinsonsRequiemAGA': ['land030.s'], 'RobinsonsRequiem': []}
INSTALL = {'RobinsonsRequiemAGA': ('_landinst', [(0xd9ba, 6), (0xdb8e, 6)])}


def assemble(variant, h1):
    if not SOURCES[variant]:
        return b'', {}
    code = CODE[variant]
    cpu = '-m68030' if variant == 'RobinsonsRequiemAGA' else '-m68000'
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b, lst = tmp / 'land.s', tmp / 'land.bin', tmp / 'land.lst'
    s.write_text(f'\t\tORG\t${code:x}\n_hunk1\tdc.l\t${h1:x}\n'
                 + ''.join(f'\t\tINCLUDE\t"{ROOT / "src" / f}"\n' for f in SOURCES[variant]))
    subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), cpu, '-devpac', '-Fbin',
                    '-quiet', '-L', str(lst), '-o', str(b), str(s)], check=True)
    data = b.read_bytes()
    syms = {}
    for line in lst.read_text(encoding='latin1').splitlines():
        f = line.split()
        if len(f) == 2 and f[1].startswith('A:'):     # absolute (ORG): A:<address>
            syms[f[0]] = int(f[1][2:], 16) - code
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return data, syms


class Land(Machine):
    def __init__(self, snap, info, variant):
        super().__init__(CPU[variant])
        uc, h = self.uc, self.h
        extra = [(0x800000, 0x300000)] if variant == 'RobinsonsRequiemAGA' else []
        for a, size in extra + [(0xbf0000, 0x10000),   # 0-$7fffff: Machine; the AGA
                                (0xdf0000, 0x10000),   # machine's fast memory to $9fffff
                                (0xf80000, 0x80000)]:  # and the patch code at $a00000
            assert uc.uc_mem_map(h, a, size, 7) == 0
        p = 0
        for a, b in info['regions']:
            self.write(a, snap[p:p + b - a])
            p += b - a

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


def variant_of(info):
    return info.get('variant', 'RobinsonsRequiem')     # ECS snapshots from before AGA's


def run_one(snap, info, patched):
    variant = variant_of(info)
    regs = info['regs']
    h1 = int(info['hunks'][1], 16)
    m = Land(snap, info, variant)
    original = m.read(h1, H1SIZE[variant])
    if patched:
        code, syms = assemble(variant, h1)
        m.write(CODE[variant], code)
        for off, label, op in PATCHES[variant]:
            m.write(h1 + off, bytes.fromhex({'jsr': '4eb9', 'jmp': '4ef9'}[op])
                    + (CODE[variant] + syms[label]).to_bytes(4, 'big'))
        if variant in INSTALL:
            label, _ = INSTALL[variant]
            stub, end = CODE[variant] + 0x80000, CODE[variant] + 0x80006
            m.write(stub, b'\x4e\xb9' + (CODE[variant] + syms[label]).to_bytes(4, 'big'))
            m.reg(REG_SR, 0x2700)
            for i, v in enumerate([0] * 8 + [h1, CODE[variant] + 0x40000] + [0] * 5
                                  + [CODE[variant] + 0xf0000]):
                m.reg((REG_D0 if i < 8 else REG_A0) + i % 8, v)
            m.run(stub, end)
            if not m.regs()[0]:
                raise RuntimeError(f'{label} did not patch')
    m.setregs(regs)
    sp = regs['sp']
    ret = int.from_bytes(m.read(sp, 4), 'big')
    m.run(h1 + LAND[variant], ret)
    sites = [(off, 6) for off, _, _ in PATCHES[variant]] + INSTALL.get(variant, ('', []))[1]
    for off, n in sites if patched else ():         # the sites back as the game has them
        m.write(h1 + off, original[off:off + n])
    mem = [m.read(a, b - a) for a, b in info['regions']]
    for i, (a, b) in enumerate(info['regions']):    # the stack's scratch below the entry
        if a <= sp - STACK_SLACK and sp <= b:
            lo, hi = sp - STACK_SLACK - a, sp - a
            mem[i] = mem[i][:lo] + bytes(hi - lo) + mem[i][hi:]
    return mem, m.regs()


def changed(x, y):
    """the number of bytes that differ between x and y, and the first's offset"""
    a = np.frombuffer(x, np.uint8)
    b = np.frombuffer(y, np.uint8)
    d = np.flatnonzero(a != b)
    return len(d), (int(d[0]) if len(d) else None)


def main():
    d = Path(sys.argv[1])
    snaps = sorted(d.glob('snap-*.json'))
    if not snaps:
        sys.exit(f'no snapshots in {d}')
    for j in snaps:
        info = json.loads(j.read_text())
        snap = j.with_suffix('.bin').read_bytes()
        a, ra = run_one(snap, info, False)
        n = changed(b''.join(a), snap)[0]
        if not PATCHES[variant_of(info)] and variant_of(info) not in INSTALL:
            print(f'{j.stem}: the landscape ran, {n} bytes changed')
            continue
        b, rb = run_one(snap, info, True)
        if a != b or ra[:15] != rb[:15]:
            for (base, _), x, y in zip(info['regions'], a, b):
                k, first = changed(x, y)
                if k:
                    print(f'{j.stem}: {k} bytes differ, first at {base + first:#x}')
            if ra[:15] != rb[:15]:
                print(f'{j.stem}: registers {[hex(x) for x in ra[:15]]} '
                      f'against {[hex(x) for x in rb[:15]]}')
            sys.exit(1)
        print(f'{j.stem}: identical ({n} bytes changed by the landscape)')


if __name__ == '__main__':
    main()
