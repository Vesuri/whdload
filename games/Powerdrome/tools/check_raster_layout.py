#!/usr/bin/env python3
"""Audit all sixteen installed fast scanline loops, including unused colours."""
import argparse
from pathlib import Path
import re
import struct
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
from perf_status import status

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--legacy', action='store_true', help='Expect original 68000/68010 loop layout')
a = p.parse_args()
s = status(a.capture/'code.bin')
base = int((a.capture/'dump-base.txt').read_text(), 0)
data = (a.capture/'code.bin').read_bytes()
chip = (a.capture/'chip.bin').read_bytes()
code, game = s['raster_code'], s['game']
raster = data[code-base:code-base+0x534+16*124+64]
word = lambda at: struct.unpack_from('>h', raster, at)[0]
trim = 0 if a.legacy else 6
assert word(0x1600c-0x15b68+12) == 0x6c-trim, 'Wrong dispatch continuation'
assert word(0x1600c-0x15b68+22) == -(0x6c-trim), 'Wrong dispatch entry'
assert s['span_resume'] in {code+0x534+124*i+0x6c-trim for i in range(16)}, 'Wrong live row continuation'
assert raster[:0x300] == chip[game+0x15b68:game+0x15e68], 'Span writers changed'
md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
for color in range(16):
    offset = 0x534+124*color
    start = code+offset
    loop = raster[offset:offset+124]
    instructions = list(md.disasm(loop, start))
    assert sum(i.size for i in instructions) == 124, 'Undecodable clone'
    boundaries = {i.address for i in instructions}
    wide = code+0x16080-0x15b68+word(0x300+2*color)
    single = code+0x1608a-0x15b68+word(0x320+2*color)
    assert start+0x60-trim+word(offset+0x60-trim) == wide, 'Wrong wide writer'
    assert start+0x6a-trim+word(offset+0x6a-trim) == single, 'Wrong single writer'
    writers = {wide, single}
    seen = set()
    for i in instructions:
        if i.mnemonic.startswith(('b', 'db')):
            target = int(re.findall(r'\$([0-9a-f]+)', i.op_str)[-1],16)
            assert target in boundaries or target in writers, 'Branch misses instruction/writer boundary'
            if target in writers:
                seen.add(target)
    assert seen == writers, 'Wrong colour writer destinations'
    assert start+0x14+struct.unpack_from('>b',loop,0x13)[0] == start+0x6c-trim, 'Empty row does not advance'
    assert start+0x72-trim+struct.unpack_from('>h',loop,0x72-trim)[0] == start+0xa, 'DBF does not repeat endpoints'
    assert code+offset+2+word(offset+2) == code+0x15ea8-0x15b68, 'Wrong mask table'
    if a.legacy:
        assert loop[0x2a:0x3c] == chip[game+0x1604a:game+0x1605c], 'Legacy plane construction changed'
    else:
        assert loop[0x2a:0x36].hex() == '47e81f4049eb1f404dec1f40', 'Unexpected plane construction'
    assert loop[0x74:] == chip[game+0x16094:game+0x1609c], 'Return sequence changed'
    assert struct.unpack_from('>I', raster, 0x534+16*124+color*4)[0] == start, 'Bad dispatch table'
print('PASS: 16 colour loops; writer targets, row branches, masks, planes, returns and dispatch table')
print('PASS: original planar span writers unchanged')
