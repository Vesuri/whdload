#!/usr/bin/env python3
"""Audit timing hook boundaries and optionally prove C3-off native hook equivalence."""
import argparse
from pathlib import Path
import re
import struct
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--off-capture',type=Path)
p.add_argument('--game',type=Path,default=Path('tmp/extracted/pd'))
a=p.parse_args()
b=a.game.read_bytes()
assert struct.unpack_from('>I',b,24)[0]==0x3e9
size=struct.unpack_from('>I',b,28)[0]*4
code=bytearray(b[32:32+size])
base=int((a.off_capture/'game-base.txt').read_text(),0) if a.off_capture else 0
pos=32+size
assert struct.unpack_from('>I',b,pos)[0]==0x3ec
pos+=4
while (count:=struct.unpack_from('>I',b,pos)[0]):
    assert struct.unpack_from('>I',b,pos+4)[0]==0
    pos+=8
    for off in struct.unpack_from(f'>{count}I',b,pos):
        struct.pack_into('>I',code,off,struct.unpack_from('>I',code,off)[0]+base)
    pos+=count*4
ranges=set()
for src in Path('whdload').glob('*.s'):
    ranges.update((int(off,16),int(n)) for off,n in re.findall(r'TIMING_RANGE h0:\$([0-9a-f]+) (\d+) bit=C3',src.read_text()))
assert ranges
m=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
for off,n in sorted(ranges):
    ins=list(m.disasm(bytes(code[off:off+n]),base+off))
    assert sum(i.size for i in ins)==n and all(i.mnemonic!='dc.w' for i in ins),f'Partial/invalid instruction at {off:#x}'
    if a.off_capture:
        for name in ('chip.bin','final-chip.bin'):
            mem=(a.off_capture/name).read_bytes()
            assert mem[base+off:base+off+n]==code[off:off+n],f'{name}: C3-off hook changed at {off:#x}'
    print(f'h0:{off:#x}: {n} bytes, {len(ins)} complete instructions')
m.skipdata=True
for ins in m.disasm(bytes(code[0x4fc0:]),base+0x4fc0):
    if not (ins.mnemonic.startswith(('b','db')) or ins.mnemonic in ('jmp','jsr')):continue
    # Branch instructions wholly removed by another timing hook cannot execute.
    if any(off<=ins.address-base and ins.address-base+ins.size<=off+n for off,n in ranges):continue
    for target in re.findall(r'\$([0-9a-f]+)',ins.op_str):
        target=int(target,16)-base
        for off,n in ranges:
            assert not off<target<off+n,f'Direct branch at {ins.address-base:#x} enters hook interior {target:#x}'
print('No decoded direct branch enters a timing hook interior')
if a.off_capture:print('All declared timing hooks are native in both C3-off snapshots')

# The input prototype reuses this body with a private a6 input structure. It must
# neither call other game code nor reference fields outside that structure.
body=list(m.disasm(bytes(code[0xd26c:0xd382]),base+0xd26c))
assert sum(i.size for i in body)==0xd382-0xd26c
for ins in body:
    assert ins.mnemonic not in ('jsr','bsr','bsr.w','bsr.b','jmp'), 'Joystick body gained an external call/jump'
    assert all(reg=='a6' for reg in re.findall(r'\ba[0-7]\b',ins.op_str)) and '(sp)' not in ins.op_str, 'Joystick body accesses memory outside private input state'
    for offset in re.findall(r'\$([0-9a-f]+)\(a6\)',ins.op_str):
        assert int(offset,16) in (0x427,0x428,0x42a,0x42e,0x432), 'Joystick body accesses non-input state'
    if ins.mnemonic.startswith(('b','db')) and not ins.mnemonic.startswith('btst'):
        targets=re.findall(r'\$([0-9a-f]+)',ins.op_str)
        assert targets and all(base+0xd26c<=int(t,16)<base+0xd382 for t in targets), 'Joystick branch leaves isolated body'
print('Reused native joystick body has only local branches and the five private input fields')

# Boost heat reuses the bounded native generator with only its seed redirected.
body=list(m.disasm(bytes(code[0x8ae6:0x8b02]),base+0x8ae6))
assert sum(i.size for i in body)==0x1c and body[-1].mnemonic=='rts'
assert [i.mnemonic for i in body]==['move.w','muls.w','addq.w','move.w','andi.w','muls.w','asl.l','swap','move.w','rts']
for ins in body[:-1]:
    assert all(reg=='a6' for reg in re.findall(r'\ba[0-7]\b',ins.op_str)) and '(sp)' not in ins.op_str
    assert all(int(off,16)==0x62 for off in re.findall(r'\$([0-9a-f]+)\(a6\)',ins.op_str))
print('Reused native heat generator touches only its private seed and d0/d1')
