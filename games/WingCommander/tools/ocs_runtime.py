#!/usr/bin/env python3
"""Discover the pinned OCS live segments; never accept a preload file copy."""
import hashlib
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
BASE, LENGTH = 0x200000, 0x400000
SIZES = (0x358c8, 0xf5b8, 4, 0x1d94)
GAME_SHA = 'eff90d6cfbc80b008e5e508ff6488f221b6e7243958aaff6fdfd0b06e6724a30'


def locate(memory):
    original = (ROOT/'tmp/originals/ocs/WingCommander/data/Wing.english').read_bytes()
    if hashlib.sha256(original).hexdigest() != GAME_SHA:
        raise ValueError('unsupported OCS English executable')
    code = original[0x2c:0x2c+SIZES[0]]
    signature = code[0x34082:0x340b0]
    def read(address, count):
        offset = address - BASE
        if not 0 <= offset <= len(memory)-count:
            raise ValueError('address outside Fast RAM snapshot')
        return memory[offset:offset+count]
    def long(address):
        return struct.unpack('>I', read(address, 4))[0]
    candidates = []
    pos = 0
    while True:
        at = memory.find(signature, pos)
        if at < 0:
            break
        pos = at+1
        h0 = BASE+at-0x34082
        try:
            hunks, address = [], h0
            for size in SIZES:
                if long(address-8) != size+8:
                    raise ValueError('not a DOS segment allocation')
                read(address, size)
                hunks.append(address)
                following = long(address-4)
                address = following*4+4
            if following != 0:
                raise ValueError('unterminated segment chain')
            # Independent relocations: entry goes to startup, whose A4 LEA
            # points into the DATA allocation, not the stored-file payload.
            if read(h0, 2) != b'\x4e\xf9' or long(h0+2) != hunks[3]+int.from_bytes(code[2:6], "big"):
                raise ValueError('entry relocation mismatch')
            if read(hunks[3]+0x14d0, 2) != b'\x49\xf9':
                raise ValueError('missing native A4 setup')
            a4 = long(hunks[3]+0x14d2)
            if a4 != hunks[1]+0x7ffe:
                raise ValueError('A4 relocation mismatch')
            if read(h0+0x272b2, 2) != b'\x4e\xf9':
                raise ValueError('not patched by the OCS slave')
            slave = long(h0+0x272b4)-0x138e
            if read(h0+0x26a3c, 2) != b'\x4e\xb9' or long(h0+0x26a3e) != slave+0x13a0:
                raise ValueError('independent slave helper mismatch')
            if read(slave+4, 8) != b'WHDLOADS':
                raise ValueError('missing slave header')
            candidates.append(dict(hunks=hunks, slave=slave, a4=a4))
        except ValueError:
            continue
    if len(candidates) != 1:
        raise ValueError(f'expected one OCS live chain; found {len(candidates)}')
    return candidates[0]
