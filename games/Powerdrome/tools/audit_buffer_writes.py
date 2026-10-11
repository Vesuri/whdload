#!/usr/bin/env python3
"""Phase C effective-address audit: CPU bitmap writes from render entry to present.

Reports every observed writer and its plane-relative extent, including HUD/timer.
Hardware blitter-register writes are reported separately; DMA is not a CPU write.
Use full 68020 traces. This is route coverage, not proof about unexecuted paths.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_020
from capstone.m68k_const import M68K_OP_MEM
import _amigaxdev
from amigaxdev import barto

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


def audit(path):
    game = int((path/'game-base.txt').read_text(), 0)
    base = int((path/'dump-base.txt').read_text(), 0)
    chip = (path/'chip.bin').read_bytes()
    other = (path/'code.bin').read_bytes()
    buffers = sorted({struct.unpack_from('>I', chip, game+0xa6e+x)[0] for x in (0x3b2, 0x3ba)})
    assert len(buffers) == 2 and all(0 < x < len(chip)-32000 for x in buffers)
    trace = barto.load(path/'trace.bin')
    regions = [(0, chip), (base, other), (0xf80000, trace.rom)]
    md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_020)
    md.detail = True
    decoded = {}
    writers = set('move movem movep clr neg negx not add addi addq addx sub subi subq subx and andi or ori eor eori bchg bclr bset tas asl asr lsl lsr rol ror roxl roxr abcd sbcd nbcd'.split())
    readonly = set('cmp cmpa cmpi cmpm tst btst muls mulu divs divu chk lea pea jmp jsr'.split())
    phase = None
    hits = {}
    unsupported = Counter()
    blitter = Counter()
    renders = weather = 0
    def label(pc):
        if game <= pc < game+0x18548:
            return 'game:'+hex(pc-game)
        if base <= pc < base+len(other):
            return 'expansion:'+hex(pc-base)
        return 'system:'+hex(pc)
    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            if pc == game+0x10df2:
                phase = 'render'
                renders += 1
            elif pc == game+0xd8ea:
                phase = 'hud'
            elif pc == game+0xf0dc:
                phase = 'timer'
            elif pc == game+0x8056:
                phase = None
            if not phase or pc is None or pc == 0x7fffffff:
                continue
            weather += pc == game+0x112f4
            if pc not in decoded:
                raw = next((data[pc-origin:pc-origin+22] for origin,data in regions if origin <= pc < origin+len(data)), b'')
                ins = next(md.disasm(raw, pc), None)
                assert ins, f'Undecodable {label(pc)}'
                decoded[pc] = (ins, raw)
            ins, raw = decoded[pc]
            name = ins.mnemonic.split('.')[0]
            ops = ins.operands
            if not ops or ops[-1].type != M68K_OP_MEM or name in readonly:
                continue
            if name not in writers and not (name.startswith('s') and name not in ('stop','swap','suba')):
                unsupported[(label(pc),ins.mnemonic)] += 1
                continue
            width = {'b':1,'w':2,'l':4}.get(ins.mnemonic[-1],1)
            if name == 'movem':
                width *= int.from_bytes(raw[2:4], 'big').bit_count()
            try:
                dest = ea(ops[-1],regs,width)
            except ValueError:
                unsupported[(label(pc),ins.mnemonic)] += 1
                continue
            if len(ops)==2 and ops[0].type==M68K_OP_MEM and ops[0].address_mode==5 and ops[-1].address_mode==5 and ops[0].reg==ops[-1].reg:
                dest -= max(width,2) if ops[-1].reg==16 else width
            if 0xdff040 <= dest < 0xdff076:
                blitter[(phase,label(pc),hex(dest-0xdff000))] += 1
            destinations = range(dest,dest+2*width,2) if name=='movep' else range(dest,dest+width)
            for bitmap in buffers:
                offsets = [byte-bitmap for byte in destinations if bitmap <= byte < bitmap+32000]
                if not offsets:
                    continue
                key = (phase,label(pc),ins.mnemonic+' '+ins.op_str)
                item = hits.setdefault(key,dict(writes=0,bytes=0,minimum=32000,maximum=0,rows=set(),outside_copy_bytes=0))
                item['writes'] += 1
                item['bytes'] += len(offsets)
                item['minimum'] = min(item['minimum'], min(offsets))
                item['maximum'] = max(item['maximum'], max(offsets))
                item['rows'].update((x%8000)//40 for x in offsets)
                item['outside_copy_bytes'] += sum(not 760 <= x%8000 < 6160 for x in offsets)
    result = dict(fields=len(trace.fields),renders=renders,weather_draws=weather,
        writers=[dict(phase=k[0],pc=k[1],instruction=k[2],**{n:sorted(v) if isinstance(v,set) else v for n,v in item.items()}) for k,item in sorted(hits.items())],
        blitter_register_writes=[dict(phase=k[0],pc=k[1],register=k[2],count=v) for k,v in sorted(blitter.items())],
        unsupported=[dict(pc=k[0],instruction=k[1],count=v) for k,v in sorted(unsupported.items())])
    return result

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path)
    args=parser.parse_args()
    result=audit(args.capture)
    print(json.dumps(result,indent=2))
    assert not result['unsupported'], 'Audit has unhandled memory operations'
