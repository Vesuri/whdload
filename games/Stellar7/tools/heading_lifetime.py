#!/usr/bin/env python3
"""Inventory observed heading reads/writes, including indirect operand aliases.

Covers explicit memory operands in captured native/slave instructions, optionally
including external code mapped in retained slow/chip snapshots. Unsupported
instructions/modes are reported, not assumed safe. Implicit stack accesses,
unmapped code, unseen paths and full actor allocation lifetimes remain outside scope.
"""
import argparse
import bisect
import collections
import json
import re
import struct
from pathlib import Path
import capstone
from capstone import m68k_const as mc
import barto
from patchlist import slave_code
from stellar7_report import locate


def signed(value, bits):
    value &= (1 << bits)-1
    return value-(1 << bits) if value & (1 << (bits-1)) else value


def accesses(insn, registers):
    """Return (address, byte count, read, write) for supported explicit operands."""
    mnemonic = insn.mnemonic.split('.')[0]
    if mnemonic in ('lea', 'pea', 'jsr', 'jmp'):
        return []  # Address calculation, not an operand memory read.
    regs = list(registers)
    size = insn.op_size.size
    if mnemonic == 'movem':
        size *= next(o.register_bits.bit_count() for o in insn.operands if o.type == mc.M68K_OP_REG_BITS)
    result = []
    for index, op in enumerate(insn.operands):
        if op.type != mc.M68K_OP_MEM:
            continue
        width = size
        if mnemonic in ('btst', 'bset', 'bclr', 'bchg', 'tas'):
            width = 1
        if mnemonic in ('move', 'movea', 'movem'):
            read, write = index == 0, index != 0
        elif mnemonic.startswith('cmp') or mnemonic in ('tst', 'btst', 'mulu', 'muls', 'divu', 'divs'):
            read, write = True, False
        elif mnemonic == 'clr' or mnemonic in ('st', 'sf', 'shi', 'sls', 'scc', 'scs', 'sne', 'seq', 'svc', 'svs', 'spl', 'smi', 'sge', 'slt', 'sgt', 'sle'):
            read, write = False, True
            if mnemonic != 'clr': width = 1
        elif mnemonic in ('add', 'adda', 'addi', 'addq', 'addx', 'sub', 'suba', 'subi', 'subq', 'subx', 'and', 'andi', 'or', 'ori', 'eor', 'eori', 'neg', 'negx', 'not', 'asl', 'asr', 'lsl', 'lsr', 'rol', 'ror', 'roxl', 'roxr', 'bset', 'bclr', 'bchg', 'tas'):
            read, write = True, index == len(insn.operands)-1
        else:
            raise ValueError('instruction '+mnemonic)
        if not width or width > 64:
            raise ValueError('operand width '+str(width))
        mode = op.address_mode
        if mode in (mc.M68K_AM_REGI_ADDR, mc.M68K_AM_REGI_ADDR_POST_INC, mc.M68K_AM_REGI_ADDR_PRE_DEC):
            register = op.reg-1
            step = max(2, width) if register == 15 else width
            if mode == mc.M68K_AM_REGI_ADDR_PRE_DEC:
                regs[register] = (regs[register]-step) & 0xffffffff
            address = regs[register]
            if mode == mc.M68K_AM_REGI_ADDR_POST_INC:
                regs[register] = (regs[register]+step) & 0xffffffff
        elif mode == mc.M68K_AM_REGI_ADDR_DISP:
            address = regs[op.mem.base_reg-1]+op.mem.disp
        elif mode in (mc.M68K_AM_AREGI_INDEX_8_BIT_DISP, mc.M68K_AM_AREGI_INDEX_BASE_DISP, mc.M68K_AM_PCI_INDEX_8_BIT_DISP, mc.M68K_AM_PCI_INDEX_BASE_DISP):
            # Capstone uses BASE_DISP for ordinary brief index with zero displacement.
            if op.mem.in_disp or op.mem.out_disp or op.mem.in_base_reg:
                raise ValueError('extended indexed displacement')
            pc_relative = mode in (mc.M68K_AM_PCI_INDEX_8_BIT_DISP, mc.M68K_AM_PCI_INDEX_BASE_DISP)
            base = insn.address+2 if pc_relative else regs[op.mem.base_reg-1]
            value = signed(regs[op.mem.index_reg-1], 32 if op.mem.index_size else 16)
            address = base+op.mem.disp+value*max(1,op.mem.scale)
        elif mode == mc.M68K_AM_PCI_DISP:
            address = insn.address+2+op.mem.disp
        elif mode == mc.M68K_AM_ABSOLUTE_DATA_SHORT:
            address = signed(op.imm, 16)
        elif mode == mc.M68K_AM_ABSOLUTE_DATA_LONG:
            address = op.imm
        else:
            raise ValueError('address mode '+str(mode))
        result.append((address & 0xffffffff, width, read, write))
    return result


def inspect(folder, listing, trace=None, include_external=False):
    folder, listing = Path(folder), Path(listing)
    assert (folder/'slave.slave').read_bytes() == listing.with_suffix('.slave').read_bytes()
    body = slave_code(folder/'slave.slave')
    symbols = {k:int(v,16) for k,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)',listing.read_text(encoding='latin1'),re.M)}
    meta = {k:int(v,0) for k,v in re.findall(r'^(code|data|base)=(\S+)',(folder/'anchor.txt').read_text(),re.M)}
    memory = (folder/'code.bin').read_bytes()
    base = locate(memory,body,meta['base'],header=32)
    assert base is not None
    count = struct.unpack_from('>h',memory,meta['data']-meta['base']+0x43b2)[0]
    assert 0 < count <= 256
    actors = set(struct.unpack_from('>'+str(count)+'I',memory,meta['data']-meta['base']+0x3fb2))
    watched = sorted(actor+94 for actor in actors)
    cpu = json.loads((folder/'metadata.json').read_text())['cpu']
    assert cpu in ('68000', '68020'), 'unsupported capture CPU '+cpu
    mode = capstone.CS_MODE_M68K_020 if cpu == '68020' else capstone.CS_MODE_M68K_000
    decoder = capstone.Cs(capstone.CS_ARCH_M68K,capstone.CS_MODE_BIG_ENDIAN|mode)
    decoder.detail = True
    decoded, epochs, current = {}, [], {}
    counts, unsupported = collections.Counter(), collections.Counter()
    prefix_reads = 0
    external_instructions = 0
    removals = collections.Counter()
    retired = set()
    producer = base+symbols['s60_geometry_heading']+10 if 's60_geometry_heading' in symbols else meta['code']+0xee8a
    geometry_entry = base+symbols['s60_geometry_compute'] if 's60_geometry_compute' in symbols else meta['code']+0xee44
    at = meta['code']-meta['base']+0x94bc
    assert memory[at:at+2] == bytes.fromhex('5379'), 'native unlink boundary changed'
    assert memory[producer-meta['base']:producer-meta['base']+4] == bytes.fromhex('3740005e')
    def label(pc):
        if meta['code'] <= pc < meta['code']+0x25360: return 'native:'+hex(pc-meta['code'])
        if base <= pc < base+len(body): return 'slave:'+hex(pc-base)
        return 'external:'+hex(pc)
    trace = trace or barto.load(folder/'trace.bin')
    for field in trace.fields:
        for pc,cost,regs in trace.instructions(field):
            if pc is None or pc == 0x7fffffff:
                continue
            own = meta['code'] <= pc < meta['code']+0x25360 or base <= pc < base+len(body)
            if not own:
                if not include_external: continue
                external_instructions += 1
            if pc == meta['code']+0x94bc:
                # The native list search found the removed actor in A3.
                # Keep watching its storage: other references can outlive unlinking.
                retired.add(regs[11]);removals['unlink_events'] += 1
                if regs[11]+94 in current:
                    current[regs[11]+94]['crossed_unlink'] = True
            if pc == geometry_entry and regs[11] in retired:
                removals['geometry_after_unlink'] += 1
                retired.remove(regs[11])
            if pc == geometry_entry and regs[11] not in actors:
                actors.add(regs[11]);bisect.insort(watched,regs[11]+94)
            if pc not in decoded:
                at = pc-meta['base']
                if 0 <= at < len(memory): instruction_bytes = memory[at:at+22]
                elif 0 <= pc < len(trace.chip): instruction_bytes = trace.chip[pc:pc+22]
                else: instruction_bytes = b''
                decoded[pc] = next(decoder.disasm(instruction_bytes,pc,count=1),None)
            insn = decoded[pc]
            if insn is None or not insn.id:
                unsupported[(label(pc),'decode')] += 1
                continue
            try:
                operands = accesses(insn,regs)
            except ValueError as error:
                unsupported[(label(pc),str(error))] += 1
                continue
            for address,width,read,write in operands:
                # A two-byte heading may overlap an access beginning one byte before it.
                low,high = bisect.bisect_left(watched,address-1),bisect.bisect_left(watched,address+width)
                for heading in watched[low:high]:
                    counts[(label(pc),read,write)] += 1
                    if read:
                        if heading in current:
                            current[heading]['reads'] += 1
                            if current[heading]['crossed_unlink']:
                                current[heading]['reads_after_unlink'] += 1
                        else: prefix_reads += 1
                    if write:
                        if heading in current:
                            old=current.pop(heading);old['ended_by_geometry']=pc==producer;epochs.append(old)
                        if pc==producer:
                            assert address==heading and width==2
                            current[heading]=dict(reads=0,field=field.index,crossed_unlink=False,reads_after_unlink=0)
    return dict(cpu=cpu,include_external=include_external,external_instructions=external_instructions,
                actor_unlink_observations=dict(removals),
                complete_epochs_crossing_unlink=sum(e['crossed_unlink'] for e in epochs),
                completed_epoch_reads_after_unlink=sum(e['reads_after_unlink'] for e in epochs),
                complete_epochs=len(epochs),unread_complete_epochs=sum(e['reads']==0 for e in epochs),
                geometry_overwrite_epochs=sum(e['ended_by_geometry'] for e in epochs),
                unread_geometry_overwrite_epochs=sum(e['reads']==0 and e['ended_by_geometry'] for e in epochs),
                incomplete_epochs=len(current),prefix_reads=prefix_reads,
                sites=[dict(pc=pc,read=read,write=write,executions=n) for (pc,read,write),n in sorted(counts.items())],
                unsupported=[dict(pc=pc,reason=why,executions=n) for (pc,why),n in sorted(unsupported.items())],scope=__doc__)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture');parser.add_argument('--listing',required=True)
    parser.add_argument('--include-external',action='store_true',help='audit external instruction bytes mapped in retained slow/chip memory too')
    args=parser.parse_args()
    print(json.dumps(inspect(args.capture,args.listing,include_external=args.include_external),indent=2))
