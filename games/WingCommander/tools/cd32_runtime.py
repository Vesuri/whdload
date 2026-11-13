#!/usr/bin/env python3
"""Locate the live CD32 hunks (English, or German) in a fast-RAM dump, rejecting PRELOAD copies."""
import hashlib
from pathlib import Path
import struct
from variants import cd32 as VARIANT
from variant_runtime import segment_chain

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x200000
SIZES = tuple(h[2] for h in VARIANT.HUNKS)
GERMAN_SIZES = (0x36064, 0xfdd4, 4, 0x15a4)   # wing.german hunk allocations


def locate(memory, german=False):
    """German: the same signature and Psygore's hook, mapped by german_map."""
    if german:
        import german_map
        m = german_map.get()
        code = m.german[0]
        first, last = (m.code(x) for x in VARIANT.SIGNATURE)
        signature = code[first:last]
        hook = m.code(0x32028)
        sizes = GERMAN_SIZES
    else:
        original = (ROOT / VARIANT.GAME).read_bytes()
        if hashlib.sha256(original).hexdigest() != VARIANT.GAME_SHA:
            raise ValueError('unsupported English executable')
        start, stored, _ = VARIANT.HUNKS[0]
        code = original[start:start+stored]
        first = VARIANT.SIGNATURE[0]
        signature = code[slice(*VARIANT.SIGNATURE)]
        hook = 0x32028
        sizes = SIZES
    candidates = []
    pos = 0
    while True:
        at = memory.find(signature,pos)
        if at < 0: break
        pos = at+1
        offset = at-first
        if offset < 8 or memory[offset+hook:offset+hook+2] != b'\x4e\xf9': continue
        slave = struct.unpack_from('>I',memory,offset+hook+2)[0]-0x178a
        if not BASE <= slave < BASE+len(memory)-0x1e0c: continue
        if struct.unpack_from('>I',memory,slave-BASE+0x121e)[0] == 0: continue
        try:
            hunks = segment_chain(memory, BASE, BASE+offset, sizes)
        except ValueError:
            continue
        candidates.append({'hunks':hunks,'slave':slave})
    if len(candidates) != 1:
        raise ValueError(f'expected one patched live segment chain; found {len(candidates)}')
    return candidates[0]
