#!/usr/bin/env python3
"""Check the eight original ray continuations that discard reciprocal D7/CCR state."""
import argparse
import struct
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--hunk', type=Path, default=Path('tmp/unpacked/h12.bin'))
a = p.parse_args()
b = a.hunk.read_bytes()
for start, quotient, coord in ((0x2998,3,0),(0x2de4,2,1),(0x3236,2,1),
                              (0x3676,3,0),(0x3ab4,3,0),(0x3f0c,2,1),
                              (0x435e,2,1),(0x479c,3,0)):
    divisor = 5 - quotient
    original = (0x2e3c, 0x0001, 0x0000, 0x8ec0 | divisor,
                0x2007 | quotient << 9, 0x4840 | quotient, 0x4247,
                0x8ec0 | divisor, 0x3007 | quotient << 9)
    assert struct.unpack_from('>9H', b, start) == original, 'unexpected original reciprocal arithmetic'
    at = start + 18
    load = at
    def word():
        global at
        value = struct.unpack_from('>H', b, at)[0]
        at += 2
        return value
    assert word() == 0x303a | coord << 9, f'h12:{load:05x}: unexpected coordinate load'
    displacement = struct.unpack_from('>h', b, at)[0]
    assert at + displacement == (8 if coord == 0 else 6), 'unexpected coordinate source'
    at += 2
    if struct.unpack_from('>H', b, at)[0] == 0x4640 | coord:
        at += 2
    overwrite = at
    expected = (0x3e00 | coord, 0x4840 | quotient, 0xcec0 | quotient,
                0x4840 | quotient, 0xc0c0 | coord << 9 | quotient,
                0x4240 | coord, 0x4840 | coord, 0xd087 | coord << 9)
    for opcode in expected:
        assert word() == opcode, f'h12:{at-2:05x}: unrecognized continuation'
    print(f'h12:{start:05x}: D7 low overwritten at {overwrite:05x}, full at {overwrite+4:05x}; '
          f'old NZVC discarded at {load:05x}, X replaced at {at-2:05x}; no old-state reader')
print('all eight continuations discard reciprocal D7/CCR before observable use')
