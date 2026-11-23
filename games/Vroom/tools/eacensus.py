#!/usr/bin/env python3
"""tools/eacensus.py TRACE LO HI [N]: the executed instructions of a Barto trace (a 68000,
the first N fields, default all) with a memory operand in [LO, HI) (hex), or an immediate in
it: PC, times, the instruction. Effective addresses come from each record's registers; an
instruction's postincrement or predecrement is not followed. For the census of what points
into a block before it moves to fast memory."""
import collections
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
import game_server  # noqa: F401,E402  (puts amigaxdev on the path)
import amigaxdev.barto as b  # noqa: E402
from capstone import *
from capstone.m68k import *
LO,HI=int(sys.argv[2],16),int(sys.argv[3],16)
t=b.load(sys.argv[1]); chip=t.chip
NF=int(sys.argv[4]) if len(sys.argv)>4 else len(t.fields)
md=Cs(CS_ARCH_M68K,CS_MODE_M68K_000); md.detail=True
dec={}
def insn(pc):
    if pc not in dec:
        l=list(md.disasm(chip[pc:pc+10],pc,1)); dec[pc]=l[0] if l else None
    return dec[pc]
def s32(v): return v-(1<<32) if v&0x80000000 else v
hits=collections.defaultdict(lambda:[0,set()])
for fi in range(NF):
    for pc,cost,r in t.instructions(t.fields[fi]):
        if pc is None or pc>=0x80000: continue
        i=insn(pc)
        if not i: continue
        for op in i.operands:
            ea=None
            if op.type==M68K_OP_MEM:
                m=op.mem; am=op.address_mode
                base=0
                if m.base_reg: 
                    bi=m.base_reg-M68K_REG_A0
                    base = r[8+bi] if 0<=bi<8 else None
                if base is None: continue
                if am in (M68K_AM_REGI_ADDR,M68K_AM_REGI_ADDR_POST_INC): ea=base
                elif am==M68K_AM_REGI_ADDR_PRE_DEC: ea=base-op.size if hasattr(op,'size') else base-2
                elif am==M68K_AM_REGI_ADDR_DISP: ea=base+m.disp
                elif am==M68K_AM_AREGI_INDEX_8_BIT_DISP:
                    x=m.index_reg; xi = r[x-M68K_REG_D0] if x<=M68K_REG_D7 else r[8+x-M68K_REG_A0]
                    if m.index_size==0: xi=(xi&0xffff); xi = xi-0x10000 if xi&0x8000 else xi  # word
                    else: xi=s32(xi)
                    ea=base+m.disp+xi
                elif am==M68K_AM_PCI_DISP: ea=pc+2+m.disp
                elif am==M68K_AM_PCI_INDEX_8_BIT_DISP:
                    x=m.index_reg; xi = r[x-M68K_REG_D0] if x<=M68K_REG_D7 else r[8+x-M68K_REG_A0]
                    xi=(xi&0xffff); xi = xi-0x10000 if xi&0x8000 else xi
                    ea=pc+2+m.disp+xi
                elif am in (M68K_AM_ABSOLUTE_DATA_SHORT,M68K_AM_ABSOLUTE_DATA_LONG): ea=op.imm
            elif op.type==M68K_OP_IMM and LO<=op.imm<HI: ea=('imm',op.imm)
            if ea is None: continue
            if isinstance(ea,tuple) or LO<=(ea&0xffffffff)<HI:
                h=hits[pc]; h[0]+=1; h[1].add(i.mnemonic+' '+i.op_str)
for pc in sorted(hits):
    print('%05x %7d %s'%(pc,hits[pc][0],'; '.join(sorted(hits[pc][1]))))
