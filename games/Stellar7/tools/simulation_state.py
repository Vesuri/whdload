#!/usr/bin/env python3
"""Compare mapped gameplay state at the same simulation boundary.

Includes all objects in world/active lists, player, power timers, RNG and stars.
Excludes raw pointers and projected coordinates, which describe drawing.
This is a mapped-state test, not a claim that every game variable is understood.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def snapshot(folder):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|data|base|frame)=(\S+)', (folder / 'anchor.txt').read_text(), re.M)}
    memory = (folder / 'code.bin').read_bytes()
    chip = (folder / 'chip.bin').read_bytes()

    def read(address, size):
        for base, blob in ((meta['base'], memory), (0, chip)):
            if base <= address and address + size <= base + len(blob):
                return blob[address-base:address-base+size]
        raise ValueError(f'Unmapped address {address:#x}, size {size}')

    data = read(meta['data'], 0x823c)
    word = lambda offset: struct.unpack_from('>H', data, offset)[0]
    long = lambda offset: struct.unpack_from('>I', data, offset)[0]
    world = [long(0x3bb0 + i*4) for i in range(word(0x3fb0))]
    active = [long(0x3fb2 + i*4) for i in range(word(0x43b2))]
    assert len(world) <= 256 and len(active) <= 256
    addresses = list(dict.fromkeys([long(0x43c0), long(0x43c4)] + world + active))
    identities = {address: i for i, address in enumerate(addresses)}
    def reference(address):
        if not address:
            return None
        if address in identities:
            return ['object', identities[address]]
        for label, base, size in [('code', meta['code'], 0x25360), ('data', meta['data'], 0x823c)]:
            if base <= address < base+size:
                return [label, address-base]
        return ['unmapped', address]  # surface unknown references, never mask them

    objects = []
    for address in addresses:
        b = read(address, 0x6e)
        objects.append(dict(
            flags=b[:2].hex(),
            type=struct.unpack_from('>H', b, 2)[0],
            distance=struct.unpack_from('>i', b, 0x50)[0],
            radius=struct.unpack_from('>i', b, 4)[0],
            position=struct.unpack_from('>3i', b, 8),
            angles=struct.unpack_from('>3H', b, 0x14),
            motion=b[0x34:0x50].hex(),
            behavior=b[0x54:0x66].hex(),
            link=reference(struct.unpack_from('>I', b, 0x66)[0]),
            owner=reference(struct.unpack_from('>I', b, 0x6a)[0]),
        ))
    # Six-byte star stride, but only x/y (first four bytes) are initialized/read
    # by $99ec/$9bd4/$9a2a. The third word is unused allocation residue.
    stars = read(long(0xee4), word(0x3b94)*6)
    result = dict(frame=word(0x1e96), level=word(0x46a0), energy=word(0x46c4),
                  score=long(0x46c8), game_counters=data[0x1e90:0x1eba].hex(), power_timers=data[0x1e9c:0x1eaa].hex(),
                  rng=hashlib.sha256(data[0x2434:0x24a8]).hexdigest(),
                  stars=hashlib.sha256(b''.join(stars[i:i+4] for i in range(0, len(stars), 6))).hexdigest(), objects=objects,
                  world=[identities[x] for x in world], active=[identities[x] for x in active])
    return result


def differences(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(a.keys() | b.keys()):
            yield from differences(a.get(key), b.get(key), f'{path}.{key}'.strip('.'))
    elif isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            yield f'{path}: length {len(a)} != {len(b)}'
        for i, (x, y) in enumerate(zip(a, b)):
            yield from differences(x, y, f'{path}[{i}]')
    elif a != b:
        yield f'{path}: {a} != {b}'


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures', nargs='+', type=Path)
    args = p.parse_args()
    states = [snapshot(c) for c in args.captures]
    if len(states) == 1:
        print(json.dumps(states[0], indent=2))
    else:
        failed = False
        for folder, state in zip(args.captures[1:], states[1:]):
            diff = list(differences(states[0], state))
            print(f'{args.captures[0]} vs {folder}: ' + ('mapped state matches' if not diff else '\n'+'\n'.join(diff)))
            failed |= bool(diff)
        raise SystemExit(int(failed))
