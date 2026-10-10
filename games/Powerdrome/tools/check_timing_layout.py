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
