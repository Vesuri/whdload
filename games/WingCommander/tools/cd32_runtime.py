#!/usr/bin/env python3
"""Locate the live English CD32 hunks in a fast-RAM dump, rejecting PRELOAD copies."""
import hashlib
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x200000
SIZES = (0x35ea4,0xfda0,4,0x1590)


def locate(memory):
    original = (ROOT/'tmp/originals/cd32/WingCommanderCD32/data/wing.english').read_bytes()
    if hashlib.sha256(original).hexdigest() != '093505483aed4c9dbd1b97484c3336e92fdb156be9c15a67ed0199bd4dade657':
        raise ValueError('unsupported English executable')
    code = original[0x2c:0x2c+SIZES[0]]
    signature = code[0x34002:0x3402e]
    candidates = []
    pos = 0
    while True:
        at = memory.find(signature,pos)
        if at < 0: break
        pos = at+1
        offset = at-0x34002
        if offset < 8 or memory[offset+0x32028:offset+0x3202a] != b'\x4e\xf9': continue
        slave = struct.unpack_from('>I',memory,offset+0x3202a)[0]-0x178a
        if not BASE <= slave < BASE+len(memory)-0x1e0c: continue
        if struct.unpack_from('>I',memory,slave-BASE+0x121e)[0] == 0: continue
        hunks = []
        address = BASE+offset
        for size in SIZES:
            off = address-BASE
            if not 8 <= off <= len(memory)-size: break
            allocated, following = struct.unpack_from('>II',memory,off-8)
            if allocated != size+8: break
            hunks.append(address)
            address = following*4+4
        if len(hunks) == 4 and following == 0:
            candidates.append({'hunks':hunks,'slave':slave})
    if len(candidates) != 1:
        raise ValueError(f'expected one patched live segment chain; found {len(candidates)}')
    return candidates[0]
