#!/usr/bin/env python3
"""Discover the pinned OCS live segments; never accept a preload file copy."""
import hashlib
from pathlib import Path
import struct
from variants import ocs as VARIANT
from variant_runtime import segment_chain

ROOT = Path(__file__).resolve().parents[1]
BASE, LENGTH = 0x200000, 0x400000
SIZES = tuple(h[2] for h in VARIANT.HUNKS)
GAME_SHA = VARIANT.GAME_SHA


def locate(memory):
    original = (ROOT / VARIANT.GAME).read_bytes()
    if hashlib.sha256(original).hexdigest() != GAME_SHA:
        raise ValueError('unsupported OCS English executable')
    start, stored, _ = VARIANT.HUNKS[0]
    code = original[start:start+stored]
    signature = code[slice(*VARIANT.SIGNATURE)]
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
        h0 = BASE+at-VARIANT.SIGNATURE[0]
        try:
            hunks = segment_chain(memory, BASE, h0, SIZES)
            # Independent relocations: entry goes to startup, whose A4 LEA
            # points into the DATA allocation, not the stored-file payload.
            if read(h0, 2) != b'\x4e\xf9' or long(h0+2) != hunks[3]+int.from_bytes(code[2:6], "big"):
                raise ValueError('entry relocation mismatch')
            if read(hunks[3]+0x14d0, 2) != b'\x49\xf9':
                raise ValueError('missing native A4 setup')
            a4 = long(hunks[3]+0x14d2)
            if a4 != hunks[1]+VARIANT.A4_BASE:
                raise ValueError('A4 relocation mismatch')
            if read(h0+VARIANT.ORIGINAL_HOOKS["clear"][1], 2) != b'\x4e\xf9':
                raise ValueError('not patched by the OCS slave')
            slave = long(h0+VARIANT.ORIGINAL_HOOKS["clear"][1]+2)-VARIANT.ORIGINAL_HOOKS["clear"][2]
            if read(h0+VARIANT.ORIGINAL_HOOKS["audio"][1], 2) != b'\x4e\xb9' or long(h0+VARIANT.ORIGINAL_HOOKS["audio"][1]+2) != slave+VARIANT.ORIGINAL_HOOKS["audio"][2]:
                raise ValueError('independent slave helper mismatch')
            if read(slave+4, 8) != b'WHDLOADS':
                raise ValueError('missing slave header')
            candidates.append(dict(hunks=hunks, slave=slave, a4=a4))
        except ValueError:
            continue
    if len(candidates) != 1:
        raise ValueError(f'expected one OCS live chain; found {len(candidates)}')
    return candidates[0]
