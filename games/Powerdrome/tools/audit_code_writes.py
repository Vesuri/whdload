#!/usr/bin/env python3
"""Find traced game memory writes overlapping executed instructions.
Uses initial chip bytes to decode instructions, including indirect destinations.
This is route coverage, not a proof about unexecuted code or writes by other tasks.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
from capstone.m68k_const import M68K_OP_MEM
import barto
from powerdrome_report import regions

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
a = p.parse_args()
if (a.capture/'game-base.txt').exists():
    base = int((a.capture/'game-base.txt').read_text(), 0)
else:
    dump_base = int((a.capture/'dump-base.txt').read_text(), 0) if (a.capture/'dump-base.txt').exists() else 0xc00000
    base = next(lo for lo,hi,name,origin in regions((a.capture/'code.bin').read_bytes(), dump_base, (a.capture/'chip.bin').read_bytes()) if name == 'game')
raw = Path('tmp/extracted/pd').read_bytes()
size = struct.unpack_from('>I', raw, 28)[0]*4
chip = (a.capture/'chip.bin').read_bytes()
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
md.detail = True
trace = barto.load(a.capture/'trace.bin')
decoded = {}
executed = set()
writes = Counter()
unsupported = Counter()
route_offsets = {0x14764: 'pit_motion', 0x10df2: 'scene_render', 0xbc7c: 'driving_present', 0x1067e: 'title_present', 0x112f4: 'weather_draw'}
route_hits = Counter()
# All memory-writing 68000 operations with an explicit destination.
writers = set('move movem movep clr neg negx not add addi addq addx sub subi subq subx and andi or ori eor eori bchg bclr bset tas asl asr lsl lsr rol ror roxl roxr abcd sbcd nbcd'.split())
readonly = set('cmp cmpa cmpi cmpm tst btst muls mulu divs divu chk lea pea jmp jsr'.split())

def ea(op, regs, width):
    mode = op.address_mode
    if mode in (3, 4, 5):
        return (regs[op.reg-1] - (max(width, 2) if op.reg == 16 else width) * (mode == 5)) & 0xffffffff
    if mode == 6:
        return (regs[op.mem.base_reg-1] + op.mem.disp) & 0xffffffff
    if mode in (7, 8):
        index = regs[op.mem.index_reg-1]
        if not op.mem.index_size:
            index = (index & 0x7fff) - (index & 0x8000)
        return (regs[op.mem.base_reg-1] + op.mem.disp + index * (op.mem.scale or 1)) & 0xffffffff
    if mode == 16:
        return ((op.imm & 0x7fff) - (op.imm & 0x8000)) & 0xffffffff
    if mode == 17:
        return op.imm & 0xffffffff
    raise ValueError(mode)

for field in trace.fields:
    for pc, cycles, regs in trace.instructions(field):
        if pc is None or not base <= pc < base+size:
            continue
        if pc-base in route_offsets:
            route_hits[route_offsets[pc-base]] += 1
        if pc not in decoded:
            ins = next(md.disasm(chip[pc:pc+22], pc), None)
            assert ins, f'Undecodable executed instruction {pc-base:#x}'
            executed.update(range(pc, pc+ins.size))
            decoded[pc] = ins
        ins = decoded[pc]
        name = ins.mnemonic.split('.')[0]
        ops = ins.operands
        if not ops or ops[-1].type != M68K_OP_MEM or name in readonly:
            continue
        if name not in writers and not (name.startswith('s') and name not in ('stop', 'swap', 'suba')):
            unsupported[(pc-base, ins.mnemonic)] += 1
            continue
        width = {'b':1, 'w':2, 'l':4}.get(ins.mnemonic[-1], 1)
        # A MOVEM mask covers a contiguous block; account for predecrement too.
        if name == 'movem':
            mask = int.from_bytes(chip[pc+2:pc+4], 'big')
            width *= mask.bit_count()
        try:
            dest = ea(ops[-1], regs, width)
        except ValueError:
            unsupported[(pc-base, ins.mnemonic)] += 1
            continue
        # Source predecrement happens before destination predecrement.
        if len(ops) == 2 and ops[0].type == M68K_OP_MEM and ops[0].address_mode == 5 and ops[-1].address_mode == 5 and ops[0].reg == ops[-1].reg:
            dest -= max(width, 2) if ops[-1].reg == 16 else width
        destinations = range(dest, dest+2*width, 2) if name == 'movep' else range(dest, dest+width)
        for byte in destinations:
            if base <= byte < base+size:
                writes[(pc-base, byte-base)] += 1
hits = [(pc, dest, n) for (pc, dest), n in writes.items() if base+dest in executed]
print(json.dumps({'fields':len(trace.fields), 'executed_instructions':len(decoded),
 'route_anchors': dict(route_hits),
 'instruction_write_bytes':[{'writer':hex(pc),'target':hex(dest),'count':n} for pc,dest,n in sorted(hits)],
 'other_written_hunk_bytes':len({dest for pc,dest in writes if base+dest not in executed}),
 'unhandled_memory_operations':[{'pc':hex(pc),'instruction':name,'count':n} for (pc,name),n in sorted(unsupported.items())]}, indent=2))
assert not unsupported, 'Audit has unhandled memory operations'
