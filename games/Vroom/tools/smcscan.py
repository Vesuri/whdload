#!/usr/bin/env python3
"""Static scan for self-modifying code in a memory image of the game.

    python3 tools/smcscan.py MEMORY.bin [--lo 0x3658 --hi 0x1e000] [--exec TRACE.bin ...]

Sweeps [lo, hi) linearly with capstone (68000) and reports
  - writes whose destination is absolute or PC-relative inside [lo, hi), and
  - LEA/PEA of an address inside [lo, hi) followed, within the next 16 instructions and
    before the register is reloaded, by a write through that address register.
With --exec, only destinations on instructions executed in the given Barto traces are
kept (data tables between routines drop out); without it, everything is listed.
A linear sweep also decodes data as code, so treat the output as candidates.
"""
import argparse
import sys

import _amigaxdev  # noqa: F401
import capstone
from capstone import m68k as M

from smc import NO_WRITE, size_of


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('memory')
    ap.add_argument('--lo', type=lambda s: int(s, 0), default=0x3658)
    ap.add_argument('--hi', type=lambda s: int(s, 0), default=0x1e000)
    ap.add_argument('--exec', nargs='*', default=[])
    a = ap.parse_args(argv)
    mem = open(a.memory, 'rb').read()
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_000)
    md.detail = True
    executed = None
    if a.exec:
        from amigaxdev import barto
        executed = set()
        for p in a.exec:
            t = barto.load(p)
            for f in t.fields:
                for pc, _, _ in t.instructions(f):
                    if pc and pc != 0x7fffffff and pc < len(mem):
                        executed.add(pc)
    def is_code(addr):
        return executed is None or any(x in executed for x in range(addr - 8, addr + 2, 2))
    insns = []
    pc = a.lo
    while pc < a.hi:
        ins = next(md.disasm(mem[pc:pc + 10], pc, 1), None)
        if ins is None or ins.id == 0:
            pc += 2
            continue
        insns.append(ins)
        pc += ins.size
    def write_dest(ins):
        base, size = size_of(ins.mnemonic)
        if base in NO_WRITE or base.startswith(('b', 'db', 'j')) and base not in ('bset', 'bclr', 'bchg'):
            return None
        if not ins.operands or ins.operands[-1].type != M.M68K_OP_MEM:
            return None
        if base == 'movem' and ins.operands[0].type == M.M68K_OP_MEM:
            return None
        return ins.operands[-1]
    out = []
    for i, ins in enumerate(insns):
        op = write_dest(ins)
        if op is not None:
            am = op.address_mode
            d = None
            if am == M.M68K_AM_PCI_DISP:
                d = ins.address + 2 + op.mem.disp
            elif am in (M.M68K_AM_ABSOLUTE_DATA_SHORT, M.M68K_AM_ABSOLUTE_DATA_LONG):
                d = op.imm & 0xffff if am == M.M68K_AM_ABSOLUTE_DATA_SHORT else op.imm
            if d is not None and a.lo <= d < a.hi and is_code(d):
                out.append((ins.address, f'{ins.mnemonic} {ins.op_str}', d))
        if ins.mnemonic in ('lea', 'lea.l') and len(ins.operands) == 2:
            src = ins.operands[0]
            am = src.address_mode
            if am == M.M68K_AM_PCI_DISP:
                d = ins.address + 2 + src.mem.disp
            elif am in (M.M68K_AM_ABSOLUTE_DATA_SHORT, M.M68K_AM_ABSOLUTE_DATA_LONG):
                d = src.imm
            else:
                continue
            if not a.lo <= d < a.hi or not is_code(d):
                continue
            reg = ins.operands[1].reg
            for nxt in insns[i + 1:i + 17]:
                op = write_dest(nxt)
                based = op is not None and (op.reg if op.address_mode in (
                    M.M68K_AM_REGI_ADDR, M.M68K_AM_REGI_ADDR_POST_INC,
                    M.M68K_AM_REGI_ADDR_PRE_DEC) else op.mem.base_reg) == reg
                if based and op.address_mode in (
                        M.M68K_AM_REGI_ADDR, M.M68K_AM_REGI_ADDR_POST_INC, M.M68K_AM_REGI_ADDR_PRE_DEC,
                        M.M68K_AM_REGI_ADDR_DISP, M.M68K_AM_AREGI_INDEX_8_BIT_DISP):
                    disp = op.mem.disp if op.address_mode == M.M68K_AM_REGI_ADDR_DISP else 0
                    out.append((nxt.address, f'{nxt.mnemonic} {nxt.op_str}  [lea ${d:X} at ${ins.address:X}]', d + disp))
                # stop when the register is reloaded
                if nxt.operands and nxt.operands[-1].type == M.M68K_OP_REG and nxt.operands[-1].reg == reg:
                    break
    for addr, text, d in out:
        print(f'${addr:X}  {text:60s} -> ${d:X}')


if __name__ == '__main__':
    main(sys.argv[1:])
