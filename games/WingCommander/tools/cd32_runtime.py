#!/usr/bin/env python3
"""Locate the live English CD32 hunks in a fast-RAM dump, rejecting PRELOAD copies."""
import hashlib
from pathlib import Path
import struct
from variants import cd32 as VARIANT
from variant_runtime import segment_chain

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x200000
SIZES = tuple(h[2] for h in VARIANT.HUNKS)


def locate(memory):
    original = (ROOT / VARIANT.GAME).read_bytes()
    if hashlib.sha256(original).hexdigest() != VARIANT.GAME_SHA:
        raise ValueError('unsupported English executable')
    start, stored, _ = VARIANT.HUNKS[0]
    code = original[start:start+stored]
    signature = code[slice(*VARIANT.SIGNATURE)]
    candidates = []
    pos = 0
    while True:
        at = memory.find(signature,pos)
        if at < 0: break
        pos = at+1
        offset = at-VARIANT.SIGNATURE[0]
        if offset < 8 or memory[offset+0x32028:offset+0x3202a] != b'\x4e\xf9': continue
        slave = struct.unpack_from('>I',memory,offset+0x3202a)[0]-0x178a
        if not BASE <= slave < BASE+len(memory)-0x1e0c: continue
        if struct.unpack_from('>I',memory,slave-BASE+0x121e)[0] == 0: continue
        try:
            hunks = segment_chain(memory, BASE, BASE+offset, SIZES)
        except ValueError:
            continue
        candidates.append({'hunks':hunks,'slave':slave})
    if len(candidates) != 1:
        raise ValueError(f'expected one patched live segment chain; found {len(candidates)}')
    return candidates[0]
