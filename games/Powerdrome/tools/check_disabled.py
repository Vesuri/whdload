#!/usr/bin/env python3
"""Check declared performance hook ranges against the relocated original game.
Use a toggle-off or no-fast-RAM capture. Proprietary bytes are read only from local inputs.
"""
import argparse
from pathlib import Path
import re
import struct
import subprocess
import sys
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--timing', action='store_true', help='Also prove all declared timing hooks retain native bytes')
p.add_argument('--game', type=Path, default=Path('tmp/extracted/pd'))
a = p.parse_args()
b = a.game.read_bytes()
assert struct.unpack_from('>I', b, 24)[0] == 0x3e9, 'Expected the supported single code hunk'
size = struct.unpack_from('>I', b, 28)[0]*4
code = bytearray(b[32:32+size])
base = int((a.capture/'game-base.txt').read_text(), 0)
pos = 32+size
assert struct.unpack_from('>I', b, pos)[0] == 0x3ec
pos += 4
while (count := struct.unpack_from('>I', b, pos)[0]):
    target = struct.unpack_from('>I', b, pos+4)[0]
    assert target == 0
    pos += 8
    for offset in struct.unpack_from(f'>{count}I', b, pos):
        value = struct.unpack_from('>I', code, offset)[0]
        struct.pack_into('>I', code, offset, value+base)
    pos += 4*count
ranges = set()
for src in Path('whdload').glob('*.s'):
    for offset, length in re.findall(r'PERF_RANGE h0:\$([0-9a-fA-F]+) (\d+) bit=C1', src.read_text()):
        ranges.add((int(offset, 16), int(length)))
assert ranges
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
for offset, length in sorted(ranges):
    decoded = list(md.disasm(bytes(code[offset:offset+length]), base+offset))
    assert sum(i.size for i in decoded) == length, f'Partial instruction at {offset:#x}'
    if offset == 0x112a6:
        # The display handshake replaces the complete TST/BEQ polling loop.
        assert length == 6 and [i.mnemonic for i in decoded] == ['tst.w', 'beq.b']
    else:
        assert len(decoded) == 1, 'Review multi-instruction hook boundaries separately'
    for name in ('chip.bin', 'final-chip.bin'):
        image = (a.capture/name).read_bytes()
        assert image[base+offset:base+offset+length] == code[offset:offset+length], f'{name}: modified hook at {offset:#x}'
    print(f'h0:{offset:#x}: {length} native bytes intact; {len(decoded)} complete instructions')
# Direct-branch audit over the disassembled original code. Embedded data can produce
# false candidates, so any hit must be inspected rather than silently ignored.
md.skipdata = True
for insn in md.disasm(bytes(code[0x4fc0:]), base+0x4fc0):
    if not (insn.mnemonic.startswith('b') or insn.mnemonic.startswith('db') or insn.mnemonic in ('jmp','jsr')):
        continue
    for target in re.findall(r'\$([0-9a-f]+)', insn.op_str):
        relative = int(target, 16)-base
        for offset, length in ranges:
            assert not offset < relative < offset+length, f'Inspect branch at {insn.address-base:#x} into hook {relative:#x}'
print('No decoded direct branch enters a hook interior')

if a.timing:
    subprocess.run([sys.executable, str(Path(__file__).with_name('check_timing_layout.py')),
                    '--off-capture', str(a.capture), '--game', str(a.game)], check=True)
