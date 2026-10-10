#!/usr/bin/env python3
"""Audit explicit game-instruction accesses to opponent projection word +$54.

Evaluates traced effective addresses, including copied/indexed pointers and block
moves. This is bounded route evidence, not an audit of unexecuted code, implicit
stack accesses, DMA or code outside the game hunk. No comparison fields are masked.
"""
import argparse
from collections import Counter
from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
from capstone.m68k_const import M68K_OP_MEM
import barto


def address(op, registers, width, pc):
    mode = op.address_mode
    if mode in (3, 4, 5):
        return (registers[op.reg-1] -
                (max(width, 2) if op.reg == 16 else width)*(mode == 5)) & 0xffffffff
    if mode == 6:
        return (registers[op.mem.base_reg-1]+op.mem.disp) & 0xffffffff
    if mode in (7, 8, 12, 13):
        index = registers[op.mem.index_reg-1]
        if not op.mem.index_size:
            index = (index & 0x7fff)-(index & 0x8000)
        base = pc+2 if mode in (12, 13) else registers[op.mem.base_reg-1]
        return (base+op.mem.disp+index*(op.mem.scale or 1)) & 0xffffffff
    if mode == 11:
        return (pc+2+op.mem.disp) & 0xffffffff
    if mode == 16:
        return ((op.imm & 0x7fff)-(op.imm & 0x8000)) & 0xffffffff
    if mode == 17:
        return op.imm & 0xffffffff
    raise ValueError(mode)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    a = p.parse_args()
    root = a.capture
    game = int((root/'game-base.txt').read_text(), 0)
    chip = (root/'chip.bin').read_bytes()
    end_chip = (root/'final-chip.bin').read_bytes()
    bank = struct.unpack_from('>I', chip, game+0xa6e+0x342)[0]
    count = struct.unpack_from('>h', chip, game+0xa6e+0x340)[0]+1
    assert count == 4
    assert end_chip[game+0xa6e+0x340:game+0xa6e+0x346] == chip[game+0xa6e+0x340:game+0xa6e+0x346], 'Opponent bank changed during capture'
    targets = {bank+i*190+0x54: i for i in range(count)}
    assert all(0 <= t < len(chip)-1 for t in targets)
    raw = Path('tmp/extracted/pd').read_bytes()
    size = struct.unpack_from('>I', raw, 28)[0]*4
    md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
    md.detail = True
    decoded, hits, unsupported = {}, Counter(), Counter()
    fresh, consumed = {}, Counter()
    trace = barto.load(root/'trace.bin')
    for field in trace.fields:
        for pc, _, regs in trace.instructions(field):
            if pc is None or not game <= pc < game+size:
                continue
            if pc == game+0x11228:
                record = regs[13]  # A5: native render-preparation caller.
                assert record+0x54 in targets
                fresh[targets[record+0x54]] = False
            if pc not in decoded:
                decoded[pc] = next(md.disasm(chip[pc:pc+22], pc), None)
            ins = decoded[pc]
            assert ins is not None and ins.mnemonic != 'dc.w'
            name = ins.mnemonic.split('.')[0]
            if name in ('lea', 'pea', 'jmp', 'jsr'):
                continue  # Computes an address; does not read its contents.
            width = {'b': 1, 'w': 2, 'l': 4}.get(ins.mnemonic[-1], 1)
            if name == 'movem':
                width *= int.from_bytes(chip[pc+2:pc+4], 'big').bit_count()
            working = list(regs)
            for index, op in enumerate(ins.operands):
                if op.type != M68K_OP_MEM:
                    continue
                try:
                    start = address(op, working, width, pc)
                except ValueError:
                    unsupported[(pc-game, ins.mnemonic, op.address_mode)] += 1
                    continue
                offsets = range(0, width*2, 2) if name == 'movep' else range(width)
                for target, pilot in targets.items():
                    if any(start+off in (target, target+1) for off in offsets):
                        hits[(pc-game, ins.mnemonic, index, pilot)] += 1
                        if pc-game in (0xa142, 0xa26e):
                            assert pilot in fresh, 'Projection write has no observed render entry'
                            fresh[pilot] = True
                        elif pc-game == 0x11644:
                            assert fresh.get(pilot), 'Drawing consumed stale or unobserved projection state'
                            consumed[pilot] += 1
                # A source postincrement/predecrement precedes the destination EA.
                if op.address_mode in (4, 5):
                    delta = max(width, 2) if op.reg == 16 else width
                    working[op.reg-1] += delta if op.address_mode == 4 else -delta
    print(f'{root.name}: {len(trace.fields)} fields; {len(decoded)} decoded game instructions')
    for (pc, mnemonic, operand, pilot), count in sorted(hits.items()):
        print(f'  h0:${pc:05x} {mnemonic}, operand {operand}, pilot {pilot+1}: {count} accesses')
    for key, count in sorted(unsupported.items()):
        print('  Unsupported:', key, count)
    assert not unsupported, 'Unresolved explicit memory addressing modes'
    assert hits, 'No projection-field accesses observed'
    observed = {key[0] for key in hits}
    assert observed <= {0xa142, 0xa26e, 0x1162e, 0x11644}, 'Additional projection-field accessor needs ownership audit'
    assert 0x11644 in observed and observed & {0xa142, 0xa26e, 0x1162e}, 'Need both producer and consumer coverage'
    assert set(consumed) == set(targets.values()), 'Need fresh producer/consumer coverage for all four pilots'
    print(f'{sum(consumed.values())} drawing reads follow fresh projection writes across all four pilots')
    print('Observed explicit accesses are confined to known projection/drawing sites; unexecuted paths remain unaudited')


if __name__ == '__main__':
    main()
