#!/usr/bin/env python3
"""The game's code, found statically: a recursive disassembly of the decrypted program.

    python3 tools/codemap.py [--pcs FILE...] summary     reached code, SP loads, PC-relative data
    python3 tools/codemap.py [--pcs FILE...] dis LO HI   the reached instructions in [LO, HI)

image() rebuilds base memory as the slave leaves it before its patches: the boot block, the
program (disk.1 $9000.. at $1AD0..$6B000) and the decryption of $6000-$13000. explore()
follows control flow from the game's entry points (entry $D7E2, the vectors it installs) and
from any traced PCs given (--pcs: callprofile pickles or text files of hex PCs), through
branches, bsr, jsr/jmp with absolute or PC-relative targets, and code addresses in immediates
(move.l #$804E,$6C). Indirect jumps through registers end a path; their targets come from the
traces or the jump tables listed in TABLES.

Used by tools/relocs.py, which builds the slave's relocation tables from it.
"""
import os
import struct
import sys
from pathlib import Path

import capstone
from capstone import m68k as M

ROOT = Path(__file__).resolve().parents[1]
DISK = ROOT / 'tmp/game/Encounter/disk.1'

ENTRY = 0xD7E2
# Entry points known from the code: the level-3 handler (installed at $E1A0), the
# division-by-zero rte ($14, set at $E1BE).
SEEDS = [ENTRY, 0x804E, 0xE288]
# Code reached only through pointers (traced): the audio sequencer's continuations (stored to
# $8266-$826E as immediates), handlers in data tables ($47F4-$4870, $10814-$10B26,
# $11346-$113B6), the jump table at $C5D6, computed jumps (jmp d8(pc,dn)), and the
# wait-for-key routine $C528 next to the key byte.
SEEDS += [0x8272, 0x8666, 0x886C, 0x8896, 0x8A46, 0x8AA4, 0x8BB6, 0x8C2E, 0x8CBC, 0x8D5E,
          0x909C, 0x9128, 0xA54A, 0xA5A4, 0xA63A, 0xA664, 0xACF8, 0xADEE, 0xAEA4, 0xC528,
          0xC774, 0xC854, 0xC95E, 0xC988, 0xCA2C, 0x107E8, 0x114CA, 0x117B4, 0x11A9E,
          0x11CC4, 0xA550, 0xC61E, 0xC8CA, 0x10822]
# Variables that hold code addresses and are only ever jumped through: the level-3 and
# division-by-zero vectors and the audio sequencer's three channel continuations (read by the
# level-3 handler, movea.l $8266,a0 / jsr (a0), at $802A-$80DA; never compared). A
# move.l #CODE,SLOT is followed as code and, in the copy, relocated (tools/relocs.py).
POINTER_SLOTS = {0x6C, 0x14, 0x8266, 0x826A, 0x826E}

_md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000)
_md.detail = True

STOP = {'rts', 'rte', 'rtr', 'illegal', 'jmp', 'bra', 'bra.s', 'bra.w', 'bra.b', 'stop'}


def image(disk=DISK):
    """Base memory as the slave leaves it after the decryption, before its patches."""
    d = open(disk, 'rb').read()
    mem = bytearray(0x80000)
    mem[0x400:0x800] = d[0x8C00:0x9000]
    mem[0x1AD0:0x6B000] = d[0x9000:0x9000 + 0x6B000 - 0x1AD0]
    d0 = 0x3491
    for a in range(0x6000, 0x13000, 2):
        x = (d0 >> 13) & 1               # asl.w #3,d1: X is bit 13 of d0
        d1 = ((d0 << 3) & 0xFFFF) ^ d0
        d1 = (d1 << 1) | x               # roxl.w #1,d1
        x, d1 = d1 >> 16, d1 & 0xFFFF
        d0 = (((d0 << 1) | x) & 0xFFFF) ^ 0xAAAA   # roxl.w #1,d0; eori.w #$AAAA,d0
        w = (mem[a] << 8 | mem[a + 1]) ^ d0
        mem[a], mem[a + 1] = w >> 8, w & 0xFF
    return mem


def decode(mem, a):
    ins = next(_md.disasm(bytes(mem[a:a + 10]), a), None)
    return ins


def branch_target(ins):
    for op in ins.operands:
        if op.type == M.M68K_OP_BR_DISP:
            return ins.address + 2 + op.br_disp.disp
    return None


def abs_target(op):
    """The address of an absolute or PC-relative memory operand, or None."""
    if op.type != M.M68K_OP_MEM:
        return None
    am = op.address_mode
    if am == M.M68K_AM_ABSOLUTE_DATA_LONG:
        return op.mem.disp & 0xffffffff if False else op.imm & 0xffffffff
    if am == M.M68K_AM_ABSOLUTE_DATA_SHORT:
        return op.imm & 0xffffffff
    return None


class Code:
    def __init__(self, mem, insns, conflicts, bad):
        self.mem, self.insns, self.conflicts, self.bad = mem, insns, conflicts, bad
        self.covered = {}
        for a, ins in insns.items():
            for b in range(a, a + ins.size):
                self.covered[b] = a

    def is_code(self, a):
        return a in self.covered


def ext_words(mem, ins):
    """The instruction's bytes as (offset, 32-bit value) pairs at every even offset after the opcode."""
    b = bytes(mem[ins.address:ins.address + ins.size])
    return [(o, struct.unpack_from('>I', b, o)[0]) for o in range(2, ins.size - 3, 2)]


def pc_rel(ins):
    """(target, mode) of a PC-relative memory operand, or None."""
    for op in ins.operands:
        if op.type == M.M68K_OP_MEM and op.address_mode == M.M68K_AM_PCI_DISP:
            return ins.address + 2 + op.mem.disp, 'disp'
        if op.type == M.M68K_OP_MEM and op.address_mode == M.M68K_AM_PCI_INDEX_8_BIT_DISP:
            return ins.address + 2 + op.mem.disp, 'index'
    return None


def immediates(mem, ins):
    """32-bit values in the instruction that could be addresses: abs.l operands and #imm.l."""
    out = []
    for op in ins.operands:
        if op.type == M.M68K_OP_MEM and op.address_mode == M.M68K_AM_ABSOLUTE_DATA_LONG:
            out.append(('abs', op.imm & 0xffffffff))
        elif op.type == M.M68K_OP_IMM and ins.op_str.startswith('#') and len(ins.bytes) >= 6:
            v = op.imm & 0xffffffff
            if ins.mnemonic.endswith('.l') or ins.mnemonic in ('movea.l',):
                out.append(('imm', v))
    return out


def pointer_store(ins):
    """(code address, slot) for move.l #CODE,SLOT with SLOT in POINTER_SLOTS, else None."""
    if ins.mnemonic != 'move.l' or len(ins.operands) != 2:
        return None
    src, dst = ins.operands
    if src.type != M.M68K_OP_IMM or dst.type != M.M68K_OP_MEM:
        return None
    if dst.address_mode not in (M.M68K_AM_ABSOLUTE_DATA_LONG, M.M68K_AM_ABSOLUTE_DATA_SHORT):
        return None
    slot = dst.imm & 0xffffffff
    return (src.imm & 0xffffffff, slot) if slot in POINTER_SLOTS else None


def explore(mem, seeds, lo=0x400, hi=0x80000, follow_imm=True):
    insns, bad = {}, set()
    work = list(seeds)
    seen_imm = set()
    while work:
        a = work.pop()
        while lo <= a < hi and a % 2 == 0 and a not in insns:
            ins = decode(mem, a)
            if ins is None:
                bad.add(a)
                break
            insns[a] = ins
            m = ins.mnemonic
            t = branch_target(ins)
            if t is not None:
                work.append(t)
            if m in ('jsr', 'jmp'):
                for op in ins.operands:
                    v = abs_target(op)
                    if v is not None:
                        work.append(v)
                pr = pc_rel(ins)
                if pr and pr[1] == 'disp':
                    work.append(pr[0])
            if follow_imm:
                for kind, v in immediates(mem, ins):
                    if kind == 'imm' and lo <= v < hi and v not in seen_imm and v % 2 == 0:
                        seen_imm.add(v)
                slot = pointer_store(ins)
                if slot is not None:
                    work.append(slot[0])
            if m in STOP or m.startswith('bra') or m == 'jmp':
                break
            a += ins.size
    conflicts = set()
    cov = {}
    for a in sorted(insns):
        for b in range(a, a + insns[a].size):
            if b in cov:
                conflicts.add((cov[b], a))
            cov[b] = a
    return Code(mem, insns, conflicts, bad), seen_imm


def load_pcs(paths):
    pcs = set()
    for p in paths:
        if p.endswith('.pkl.gz'):
            sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
            from amigaxdev.callprofile import Reduction
            pcs |= {pc for pc in Reduction.load(p).self if isinstance(pc, int) and pc < 0x80000}
        else:
            pcs |= {int(w, 16) for w in open(p).read().split()}
    return pcs


def build(pcs=()):
    mem = image()
    code, _ = explore(mem, SEEDS + sorted(pcs))
    return code


def main(argv):
    pcs_files = []
    while argv and argv[0] == '--pcs':
        pcs_files.append(argv[1])
        argv = argv[2:]
    pcs = load_pcs(pcs_files)
    code = build(pcs)
    if argv[0] == 'summary':
        static = build(())
        print(f'reached instructions: {len(code.insns)} (from the entry points alone {len(static.insns)}); '
              f'traced PCs {len(pcs)}, of them not reached statically {len(pcs - set(static.insns))}')
        print(f'overlapping instructions: {len(code.conflicts)}; undecodable: {sorted(map(hex, code.bad))}')
        rng = sorted(code.insns)
        print(f'range ${rng[0]:05x}-${rng[-1]:05x}')
    elif argv[0] == 'dis':
        lo, hi = int(argv[1], 16), int(argv[2], 16)
        for a in sorted(code.insns):
            if lo <= a < hi:
                ins = code.insns[a]
                print(f'{a:05x}  {ins.bytes.hex():20} {ins.mnemonic} {ins.op_str}')


if __name__ == '__main__':
    main(sys.argv[1:])
