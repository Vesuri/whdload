#!/usr/bin/env python3
"""Validate native input-entry/return observations during actual terrain contact."""
import argparse
import json
import re
import struct
from pathlib import Path
from encounter_state import read as encounter, validate_terrain
from sim60_state import read as clock, build_constant
from simulation_state import snapshot


def point(folder):
    text = (folder/'anchor.txt').read_text()
    meta = {k: int(v, 0) for k, v in re.findall(r'^(code|data|base)=(\S+)', text, re.M)}
    pc = re.search(r'^pc\s+0x([0-9a-f]+)', text, re.M)
    assert pc, 'native PC observation missing'
    memory = (folder/'code.bin').read_bytes()
    data = meta['data']-meta['base']
    actor = struct.unpack_from('>I', memory, data+0x43c0)[0]-meta['base']
    assert 0 <= actor <= len(memory)-112
    return meta, int(pc[1], 16)-meta['code'], memory[actor:actor+112]


def validate(folder, listing):
    folder, listing = Path(folder), Path(listing)
    assert (folder/'slave.slave').read_bytes() == listing.with_suffix('.slave').read_bytes()
    paths = sorted((folder/'events').iterdir())
    assert paths
    n = clock(paths[0])['substeps']
    count = (28*n+11)//12+1
    first_tick = build_constant(listing, 'BOSS_TERRAIN_TEST')+(3*n+11)//12
    assert len(paths) == count
    validate_terrain(encounter(paths[0], listing))
    results = []
    last = None
    meaningful_skips = 0
    for index, before in enumerate(paths):
        after = before/'after'
        bm, bp, ba = point(before)
        am, ap, aa = point(after)
        assert bm == am and bp == 0x100a8 and ap == 0x100d6
        bs, ast = snapshot(before), snapshot(after)
        bc, ac = clock(before), clock(after)
        tick = bc['ticks']
        assert bc['substeps'] == ac['substeps'] == n
        assert tick == ac['ticks'] == first_tick+index
        assert bc['running'] == ac['running'] == 1
        assert bc['rendering'] == ac['rendering'] == 0
        assert bs['level'] == ast['level'] == 5
        assert bs['terrain_contact'] == ast['terrain_contact']
        old = struct.unpack('>HHI', bytes.fromhex(bs['terrain_friction_clock']))
        new = struct.unpack('>HHI', bytes.fromhex(ast['terrain_friction_clock']))
        assert old == ((0, 0, 0) if last is None else (1, 0, last))
        contact = bool(bs['terrain_contact'])
        due = contact and (last is None or tick-last >= n)
        expected = bytearray(ba)
        speeds = [struct.unpack_from('>h', ba, offset)[0] for offset in (56, 64)]
        if due:
            for offset, value in zip((56, 64), speeds):
                struct.pack_into('>h', expected, offset, value >> 2)
            last = tick
        elif contact and any(value != value >> 2 for value in speeds):
            meaningful_skips += 1
        assert aa == expected, (tick, speeds, due)
        assert new == ((0, 0, 0) if last is None else (1, 0, last)), (tick, old, new)
        results.append(dict(tick=tick, contact=contact, damping=due, before=speeds,
                            after=[struct.unpack_from('>h', aa, offset)[0] for offset in (56, 64)]))
    due_ticks = [row['tick'] for row in results if row['damping']]
    assert len(due_ticks) >= 2 and (meaningful_skips >= 2 if n > 1 else meaningful_skips == 0), (due_ticks, meaningful_skips)
    return dict(events=results, damping_ticks=due_ticks, meaningful_skips=meaningful_skips,
                scope='Explicit boss-state setup; native type-46 contact and complete player actor comparison across the input damping block.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.capture, args.listing), indent=2))
