#!/usr/bin/env python3
"""Find self-modifying code in Barto traces: CPU writes that land on executed instruction bytes.

    python3 tools/smc.py TRACE.bin [TRACE.bin ...] [--lo 0x1000 --hi 0x80000]

Every instruction record of every field is decoded (capstone, 68000) from the trace's Chip
snapshot; its memory destination is evaluated from the record's registers (the state before
the instruction executes). A write whose bytes overlap any instruction executed anywhere in the
given traces is reported once per writer PC, with the destinations and values it wrote.
A writer that only hits data (tables between routines) is not reported: no instruction ran there.
"""
import argparse
import collections
import struct
import sys

import _amigaxdev  # noqa: F401
from amigaxdev import barto
import capstone
from capstone import m68k as M

# Instructions that never write their last operand (or write only registers).
NO_WRITE = {'cmp', 'cmpi', 'cmpa', 'cmpm', 'tst', 'btst', 'chk', 'lea', 'pea', 'jmp', 'jsr',
            'bra', 'bsr', 'rts', 'rte', 'rtr', 'link', 'unlk', 'trap', 'stop', 'nop', 'dbf',
            'dbra', 'movea', 'moveq', 'swap', 'ext', 'exg', 'muls', 'mulu', 'divs', 'divu',
            'reset', 'illegal', 'trapv'}


def size_of(mn):
    base, _, suf = mn.partition('.')
    return base, {'b': 1, 'w': 2, 'l': 4, 's': 1}.get(suf, 0)


def ea(op, regs, pc, size):
    """Address a memory operand refers to (pre-decrement applied), or None."""
    m = op.mem
    am = op.address_mode
    def reg(r):
        if M.M68K_REG_D0 <= r <= M.M68K_REG_D7:
            return regs[r - M.M68K_REG_D0]
        if M.M68K_REG_A0 <= r <= M.M68K_REG_A7:
            return regs[8 + r - M.M68K_REG_A0]
        return 0
    def index():
        v = reg(m.index_reg)
        if m.index_size == 0:  # word index
            v &= 0xffff
            v -= 0x10000 if v & 0x8000 else 0
        return v * (m.scale or 1)
    # capstone gives (An), (An)+ and -(An) their register in op.reg, not mem.base_reg
    if am == M.M68K_AM_REGI_ADDR or am == M.M68K_AM_REGI_ADDR_POST_INC:
        return reg(op.reg)
    if am == M.M68K_AM_REGI_ADDR_PRE_DEC:
        return reg(op.reg) - size
    if am == M.M68K_AM_REGI_ADDR_DISP:
        return reg(m.base_reg) + m.disp
    if am == M.M68K_AM_AREGI_INDEX_8_BIT_DISP:
        return reg(m.base_reg) + m.disp + index()
    if am == M.M68K_AM_PCI_DISP:
        return pc + 2 + m.disp
    if am == M.M68K_AM_PCI_INDEX_8_BIT_DISP:
        return pc + 2 + m.disp + index()
    if am in (M.M68K_AM_ABSOLUTE_DATA_SHORT, M.M68K_AM_ABSOLUTE_DATA_LONG):
        v = op.imm
        if am == M.M68K_AM_ABSOLUTE_DATA_SHORT and v & 0x8000:
            v -= 0x10000
        return v
    return None


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('traces', nargs='+')
    ap.add_argument('--lo', type=lambda s: int(s, 0), default=0x400)
    ap.add_argument('--hi', type=lambda s: int(s, 0), default=0x200000)
    a = ap.parse_args(argv)
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000)
    md.detail = True
    executed = set()
    writes = []  # (writer pc, addr, size, text)
    for path in a.traces:
        t = barto.load(path)
        mem = bytes(t.chip)
        cache = {}
        for f in t.fields:
            for pc, cost, regs in t.instructions(f):
                if pc is None or pc == 0x7fffffff or not a.lo <= pc < min(a.hi, len(mem)):
                    continue
                ins = cache.get(pc)
                if ins is None:
                    ins = next(md.disasm(mem[pc:pc + 10], pc, 1), False)
                    cache[pc] = ins
                if not ins or ins.id == 0:
                    continue
                executed.update(range(pc, pc + ins.size))
                base, size = size_of(ins.mnemonic)
                if base in NO_WRITE or base.startswith(('b', 'db', 'j')) and base not in (
                        'bset', 'bclr', 'bchg'):
                    continue
                ops = ins.operands
                if not ops:
                    continue
                if base == 'movem':
                    if ops[-1].type != M.M68K_OP_MEM:
                        continue
                    n = bin(ops[0].register_bits).count('1') if hasattr(ops[0], 'register_bits') else 1
                    addr = ea(ops[-1], regs, pc, size)
                    if addr is None:
                        continue
                    if ops[-1].address_mode == M.M68K_AM_REGI_ADDR_PRE_DEC:
                        addr = addr + size - n * size
                    writes.append((pc, addr & 0xffffffff, n * size, ins.mnemonic + ' ' + ins.op_str, regs))
                    continue
                op = ops[-1]
                if op.type != M.M68K_OP_MEM:
                    continue
                if base in ('bset', 'bclr', 'bchg', 'tas') or base.startswith('s') and len(base) <= 3:
                    size = 1
                addr = ea(op, regs, pc, size or 2)
                if addr is None:
                    continue
                writes.append((pc, addr & 0xffffffff, size or 2, ins.mnemonic + ' ' + ins.op_str, regs))
    hits = collections.defaultdict(list)
    for pc, addr, size, text, regs in writes:
        if any(b in executed for b in range(addr, addr + size)):
            hits[(pc, text)].append(addr)
    if not hits:
        print('no writes to executed code')
    for (pc, text), addrs in sorted(hits.items()):
        c = collections.Counter(addrs)
        dests = ', '.join(f'${d:X}x{n}' for d, n in sorted(c.items())[:8])
        print(f'${pc:X}  {text:40s} -> {dests}{" ..." if len(c) > 8 else ""}')
    print(f'{len(executed)} executed bytes, {len(writes)} memory writes', file=sys.stderr)


if __name__ == '__main__':
    main(sys.argv[1:])
