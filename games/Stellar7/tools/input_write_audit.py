#!/usr/bin/env python3
"""Inventory player velocity writes in the supplied native input routine.

This is a static scope check, not a claim of complete hardware-input coverage.
It checks every destination using the player's two velocity displacements in
this routine, and maps each increment to a guarded quanta-table instruction.
"""
import json
import re
import struct
from pathlib import Path
import capstone
from stellar7_report import GAME, CODE_FILE, CODE_SIZE


SCALED = {
    0xfeb0: (0xfea8, 80), 0xfebe: (0xfeb6, 80),
    0xfed8: (0xfed0, 80), 0xfee6: (0xfede, 80),
    0xff20: (0xff1e, 80), 0xff28: (0xff26, 80),
    0xffa4: (0xffa2, 10), 0xffb2: (0xffb0, 10),
    0x1002c: (0x1002a, 10), 0x10034: (0x10032, 10),
    0x1006c: (0x1006a, 80), 0x10074: (0x10072, 80),
    0x10088: (0x10080, 40),
}
GROUPS = {
    'scaled_increment': set(SCALED),
    'zero_clamp': {0xff10, 0x1001c, 0x1005c},
    'speed_limit': {0xff5c, 0xffe8, 0x100a4},
    'direct_assignment': {0xfe94, 0xff98},
    'clocked_terrain_damping': {0x100c2, 0x100d2},
}
THRESHOLDS = {0xff02: 80, 0x1000e: 10, 0x1004e: 80}


def inspect():
    code = Path(GAME).read_bytes()[CODE_FILE:CODE_FILE+CODE_SIZE]
    decoder = capstone.Cs(capstone.CS_ARCH_M68K,
                          capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    rows = []
    position = 0xfcf4
    for instruction in decoder.disasm(code[0xfcf4:0x100de], 0xfcf4):
        assert instruction.address == position and instruction.id
        position += instruction.size
        if not re.search(r'\$(?:38|40)\(a[0-7]\)$', instruction.op_str):
            continue
        if instruction.mnemonic.startswith(('cmp.', 'cmpi.', 'tst.')):
            continue
        groups = [name for name, sites in GROUPS.items() if instruction.address in sites]
        assert len(groups) == 1, ('unclassified velocity destination', instruction)
        rows.append(dict(offset=hex(instruction.address), kind=groups[0],
                         instruction=instruction.mnemonic+' '+instruction.op_str))
    assert position == 0x100de
    assert {int(row['offset'], 16) for row in rows} == set.union(*GROUPS.values())
    source = (Path(__file__).resolve().parent.parent/'whdload/motion60.s').read_text()
    table = source.split('S60_INPUT_ENTRIES MACRO', 1)[1].split('        ENDM', 1)[0]
    entries = {int(site, 16): (int(opcode, 16), int(row)) for site, opcode, row in
               re.findall(r'S60_INPUT_SITE \$([0-9a-f]+),\$([0-9a-f]+),(\d+)', table)}
    expected = dict(THRESHOLDS)
    expected.update(value for value in SCALED.values())
    assert set(entries) == set(expected) and len(entries) == 16
    for site, amount in expected.items():
        opcode, row = entries[site]
        assert struct.unpack_from('>H', code, site)[0] == opcode
        assert opcode & 0xf100 == 0x7000 and opcode & 0xff == amount
        assert row == {80: 0, 10: 12, 40: 24}[amount]
    quanta = source.split('s60_input_values:', 1)[1].split('EVEN', 1)[0]
    values = [list(map(int, row.split(','))) for row in re.findall(r'dc\.b ([\d,]+)', quanta)]
    assert values == [[((phase+1)*amount)//12-(phase*amount)//12 for phase in range(12)]
                      for amount in (80, 10, 40)]
    return dict(writes=rows, counts={name: len(sites) for name, sites in GROUPS.items()},
                scaled_constant_sites=len(entries),
                scope='Static native input routine $fcf4–$100dc and the current quanta table. Direct device values, keyboard callbacks and real controls require separate evidence.')


if __name__ == '__main__':
    print(json.dumps(inspect(), indent=2))
