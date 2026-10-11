#!/usr/bin/env python3
"""Check observed native terrain contacts from raw before/after snapshots.

Requires the explicit BE64 boss-state setup; this does not validate the random
choice to enter that state. Native allocation and contacts must actually occur.
"""
import argparse
import json
import re
import struct
from pathlib import Path
from encounter_state import read as encounter, validate_terrain
from sim60_state import read as clock, build_constant
from simulation_state import snapshot


def registers(folder):
    text = (folder/'anchor.txt').read_text()
    meta = {k: int(v, 0) for k, v in re.findall(r'^(code|data|base)=(\S+)', text, re.M)}
    regs = {k: int(v, 16) for k, v in re.findall(r'^(pc|a3|d0)\s+0x([0-9a-f]+)', text, re.M)}
    assert 'pc' in regs, 'missing stopped PC'
    return meta, regs


def validate(folder, listing):
    folder, listing = Path(folder), Path(listing)
    events = sorted((folder/'events').iterdir())
    assert events and all(p.is_dir() for p in events)
    results = []
    last_damage = None
    for path in events:
        meta, regs = registers(path)
        after = path/'after'
        assert after.is_dir(), 'death/boundary stop is not successful contact evidence'
        after_meta, after_regs = registers(after)
        assert meta == after_meta
        before_state, after_state = snapshot(path), snapshot(after)
        before_clock, after_clock = clock(path), clock(after)
        tick = before_clock['ticks']
        n = before_clock['substeps']
        assert after_clock['substeps'] == n
        assert after_clock['ticks'] == tick and before_clock['running'] and after_clock['running']
        assert before_state['level'] == after_state['level'] == 5
        setup = encounter(path, listing)
        validate_terrain(setup)
        assert setup['terrain_tick'] == build_constant(listing, 'BOSS_TERRAIN_TEST')
        memory = (path/'code.bin').read_bytes()
        actor = regs['a3']-meta['base']
        assert 0 <= actor <= len(memory)-0x6e
        actor_type = struct.unpack_from('>H', memory, actor+2)[0]
        pc = regs['pc']-meta['code']
        if pc == 0x11472:
            assert not results and actor_type == 44
            assert after_regs['pc'] == meta['code']+0x11476
            pointer = after_regs['d0']-meta['base']
            after_memory = (after/'code.bin').read_bytes()
            assert 0 <= pointer <= len(after_memory)-0x6e, 'native allocation failed'
            assert struct.unpack_from('>H', after_memory, pointer+2)[0] == 46
            assert before_state['energy'] == after_state['energy']
            results.append(dict(kind='spawn', tick=tick))
            continue
        assert results and results[0]['kind'] == 'spawn'
        assert pc == 0x36f8 and actor_type == 46
        assert after_regs['pc'] == meta['code']+0x36fe
        old = struct.unpack('>HHI', bytes.fromhex(before_state['terrain_clock']))
        new = struct.unpack('>HHI', bytes.fromhex(after_state['terrain_clock']))
        due = not old[0] or ((tick-old[2]) & 0xffffffff) >= n
        expected_energy = (before_state['energy']-int(due)) & 0xffff
        assert after_state['energy'] == expected_energy, (tick, before_state, after_state)
        if due:
            assert new == (1, old[1], tick), (tick, old, new)
            if last_damage is not None:
                assert tick-last_damage >= n
            last_damage = tick
        else:
            assert new == old
        results.append(dict(kind='contact', tick=tick, damage=int(due),
                            energy_before=before_state['energy'], energy_after=after_state['energy']))
    contacts = [r for r in results if r['kind'] == 'contact']
    assert len(contacts) == 2*n+1
    assert [r['tick'] for r in contacts] == list(range(contacts[0]['tick'], contacts[0]['tick']+2*n+1))
    damage_ticks = [r['tick'] for r in contacts if r['damage']]
    assert damage_ticks == [contacts[0]['tick']+i for i in (0, n, 2*n)], damage_ticks
    return dict(events=results, damage_ticks=damage_ticks, contact_count=len(contacts),
                scope='Explicit boss-state setup; native allocation/contact and raw energy/clock checks')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.capture, args.listing), indent=2))
