#!/usr/bin/env python3
"""Check C3/C4 hook instructions and native direct entries in modal/loop regions."""
from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000, CS_MODE_BIG_ENDIAN
from capstone.m68k import M68K_OP_BR_DISP, M68K_OP_MEM
from check_disabled import SOURCE, ranges, relocated_original
from slave_inputs import verify


def check():
    verify()
    bases = (0x100000, 0x200000, 0x300000, 0x400000)
    hunks = relocated_original(bases)
    cs = Cs(CS_ARCH_M68K, CS_MODE_M68K_000 | CS_MODE_BIG_ENDIAN)
    cs.detail = True
    expected = {0x3c962:(0,0x3b5de), 0x3ccba:(0,0x3b80e),
                0x3b6de:(2,0x8e2), 0x3b8b4:(2,0x8e2),
                0x3ba24:(0,0x3ca5a), 0x3cbd6:(0,0x39fd2), 0x3ca26:(2,0x8e2),
                0x3c94a:(0,0x64), 0x3cc8e:(0,0x64)}      # C4 key scans
    annotations = {r['offset']:r for r in ranges(SOURCE.read_text()) if r['hunk']==0}
    for offset, (h,target) in expected.items():
        ins = next(cs.disasm(hunks[0][offset:offset+6],bases[0]+offset))
        assert ins.mnemonic == 'jsr' and ins.size == 6
        assert ins.operands[0].imm == bases[h]+target, hex(offset)
        assert annotations[offset]['size'] == 6
    targets = set()
    count = 0
    for start,end in ((0x3b5de,0x3b95e+2),(0x3b960,0x3bab4),(0x3c8d2,0x3cd10)):
        instructions = list(cs.disasm(hunks[0][start:end],bases[0]+start))
        assert sum(i.size for i in instructions)==end-start
        for ins in instructions:
            count += 1
            for op in ins.operands:
                if op.type == M68K_OP_BR_DISP:
                    targets.add(ins.address+2+op.br_disp.disp)
                elif ins.mnemonic in ('jsr','jmp') and op.type == M68K_OP_MEM:
                    targets.add(op.imm)
    def interior(offset):
        return any(bases[0]+offset < target < bases[0]+offset+6 for target in targets)
    assert not any(interior(offset) for offset in expected)
    # A displaced hook spanning the live loop head must be rejected.
    assert interior(0x3c8f4)
    print(f'{len(expected)} C3/C4 calls and {count} native instructions checked; interior-entry negative fixture rejected')


if __name__ == '__main__':
    check()
