#!/usr/bin/env python3
"""Inventory relocated absolute accesses to the native game clock (hunk $f96).

Relocations supply the reference inventory independently of the linear decoder.
This does not prove absence of computed pointers or identify every caller/domain.
No game bytes or generated disassembly should be committed.
"""
import argparse
from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--game', type=Path, default=Path('tmp/extracted/pd'))
a = p.parse_args()
b = a.game.read_bytes()
assert struct.unpack_from('>I', b, 24)[0] == 0x3e9
size = struct.unpack_from('>I', b, 28)[0] * 4
code = b[32:32+size]
pos = 32 + size
assert struct.unpack_from('>I', b, pos)[0] == 0x3ec
pos += 4
references = []
while (count := struct.unpack_from('>I', b, pos)[0]):
    assert struct.unpack_from('>I', b, pos+4)[0] == 0
    pos += 8
    for off in struct.unpack_from(f'>{count}I', b, pos):
        assert off+4 <= size
        if struct.unpack_from('>I', code, off)[0] == 0xf96:
            references.append(off)
    pos += 4*count
assert len(references) == len(set(references)) == 85, 'Clock reference inventory changed'
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
md.skipdata = True
instructions = list(md.disasm(code[0x4fc0:], 0x4fc0))
writers = {0x5414:'reset', 0x59f2:'TOD accumulation', 0x93d2:'restore from a3',
           0x93fc:'restore from saved input state', 0xbeec:'pause restore',
           0xf67a:'gameplay time adjustment'}
seen_writers = set()
reads = 0
for ref in sorted(references):
    found = [i for i in instructions if i.address <= ref and ref+4 <= i.address+i.size]
    assert len(found) == 1 and found[0].mnemonic != 'dc.w', 'Undecoded clock relocation'
    i = found[0]
    operands = i.op_str.split(', ')
    assert '$f96.l' in operands, 'Clock relocation is not a direct absolute operand'
    if operands[-1] == '$f96.l':
        assert i.address in writers and i.mnemonic in ('move.l', 'add.l')
        seen_writers.add(i.address)
        kind = 'read/write' if i.mnemonic == 'add.l' else 'write'
        detail = writers[i.address]
    else:
        assert operands[0] == '$f96.l' and i.mnemonic in ('move.l', 'cmp.l', 'add.l')
        kind, detail = 'read', 'consumer'
        reads += 1
    print(f'h0:${i.address:05x}: {kind}: {detail}')
assert seen_writers == set(writers)
assert reads == 79
print('85 relocated absolute references: 79 read-only, 4 stores, 2 read/modify/writes')
print('Indirect aliases and transitive calling contexts still require separate audits')

# Opponent updates also occur outside the ordinary world body. These callers
# must be included when choosing the repair/lap timestamp domain.
opponent_calls = {i.address for i in instructions
                  if i.mnemonic in ('bsr.w', 'jsr') and i.op_str in ('$d3d6', '$d3d6.l')}
assert opponent_calls == {0xb76c, 0xc92c, 0xced8, 0xe3bc, 0xfe40, 0xffc2, 0x1318c}
print('Direct native opponent-update callers: ' + ', '.join(f'h0:${off:05x}' for off in sorted(opponent_calls)))
