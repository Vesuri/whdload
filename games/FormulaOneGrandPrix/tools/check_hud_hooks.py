#!/usr/bin/env python3
"""Reject C2 HUD hooks that overwrite a native branch/call entry.

Traverse the relevant original HUD routines from known entry points, then check
all direct targets against the optional patch inventory. Unknown edges fail closed.
No original bytes are written. Requires Capstone 5.
"""
from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000, CS_MODE_BIG_ENDIAN
from capstone.m68k import M68K_OP_BR_DISP, M68K_OP_MEM

from check_disabled import SOURCE, ranges, relocated_original
from slave_inputs import verify

ROOTS = (0x1dc7a, 0x1dc9e, 0x1dce0, 0x1ddc0, 0x1def6, 0x1df80, 0x1e008, 0x1e9f4,
         0x1eb50, 0x1efdc, 0x1f8dc, 0x1f966, 0x1f9ea)


def check(source):
    verify()
    bases = (0x100000, 0x200000, 0x300000, 0x400000)
    hunks = relocated_original(bases)
    decoder = Cs(CS_ARCH_M68K, CS_MODE_M68K_000 | CS_MODE_BIG_ENDIAN)
    decoder.detail = True
    pending = [bases[2]+offset for offset in ROOTS]
    visited, targets = set(), set()
    while pending:
        pc = pending.pop()
        if pc in visited:
            continue
        visited.add(pc)
        h = next((h for h in (0,2) if bases[h] <= pc < bases[h]+len(hunks[h])), None)
        if h is None:
            raise ValueError('HUD traversal left executable hunks')
        offset = pc-bases[h]
        insn = next(decoder.disasm(hunks[h][offset:offset+24], pc, count=1), None)
        if insn is None or insn.mnemonic == 'dc.w':
            raise ValueError(f'invalid instruction at h{h}+{offset:x}')
        op = insn.mnemonic.split('.')[0]
        if op in ('rts','rte','rtr'):
            continue
        branch = (op in ('jsr','jmp','bsr','bra') or op.startswith('db')
                  or (op.startswith('b') and op not in ('btst','bset','bclr','bchg')))
        if branch:
            operand = insn.operands[-1]
            if operand.type == M68K_OP_BR_DISP:
                target = pc+2+operand.br_disp.disp
            elif operand.type == M68K_OP_MEM and operand.address_mode in (16,17):
                target = operand.imm
            elif operand.type == M68K_OP_MEM and operand.address_mode == 11:
                target = pc+2+operand.mem.disp
            else:
                raise ValueError(f'unresolved HUD edge at h{h}+{offset:x}')
            targets.add(target)
            pending.append(target)
        if op not in ('jmp','bra'):
            pending.append(pc+insn.size)
    failures = []
    for item in ranges(source):
        start = bases[item['hunk']]+item['offset']
        for target in targets:
            if start < target < start+item['size']:
                failures.append(f'h{item["hunk"]}+{item["offset"]:x}: entry +{target-start}')
    return len(visited), failures


if __name__ == '__main__':
    source = SOURCE.read_text()
    count, failures = check(source)
    if failures:
        raise SystemExit('\n'.join(failures))
    # The actual rejected glyph placement is a regression fixture made only of
    # offsets: its final stolen instruction was also the row-loop branch target.
    bad = source.replace('h2:1f128 6', 'h2:1f12e 6').replace(
        'PL_P $8e4bc,c2_hud_glyph', 'PL_P $8e4c2,c2_hud_glyph')
    if bad == source or not check(bad)[1]:
        raise AssertionError('overwritten glyph loop entry was not rejected')
    print(f'{count} native HUD instructions checked; interior entries rejected; negative fixture rejected')
