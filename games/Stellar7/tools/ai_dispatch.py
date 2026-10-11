#!/usr/bin/env python3
"""Audit generic AI dispatch cadence in an exact retained simulation trace.

Requires the listing and sibling .slave from the same build. This checks the
observed route, not unobserved state transitions or projectile creation effects.
"""
import argparse
import collections
import json
import re
import struct
from pathlib import Path
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
import sim60_state
from stellar7_report import locate


def gate_sites(body, offsets):
    """Recognize the complete decision gate with byte or word BNE encoding."""
    step = offsets['s60_loop_step']
    logic = struct.pack('>h', offsets['s60_logic']-offsets['s60_last'])
    phase = struct.pack('>h', offsets['s60_phase']-offsets['s60_last'])
    prefix = bytes.fromhex('426a')+logic+bytes.fromhex('4a6a')+phase
    setter = bytes.fromhex('357c0001')+logic
    matches = []
    # Both branches skip the six-byte setter. Word displacement is relative
    # to the extension word, not the end of that instruction.
    for branch in (bytes.fromhex('6606'), bytes.fromhex('66000008')):
        sequence = prefix+branch+setter
        start = step-len(sequence)
        if start >= 0 and body[start:step] == sequence:
            matches.append((start, step-len(setter)))
    assert len(matches) == 1, 'unrecognized scheduler decision gate'
    return matches[0]


def inspect(folder, listing):
    folder, listing = Path(folder), Path(listing)
    n = sim60_state.read(folder)['substeps']
    slave = (folder/'slave.slave').read_bytes()
    assert slave == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    symbols = listing.read_text(encoding='latin1')
    offsets = {name: int(re.search(r'^'+name+r'\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
               for name in ('s60_update', 's60_ai', 's60_loop_step', 's60_loop_complete',
                            's60_logic', 's60_phase', 's60_last')}
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|data|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', slave, 28)[0]*4
    base = locate(memory, slave[32:32+size], meta['base'], header=32)
    assert base is not None
    native_table = (0, 0xeec4, 0xf136, 0xf192, 0xf328, 0x10904)
    for index, target in enumerate(native_table):
        actual = struct.unpack_from('>I', memory, meta['data']-meta['base']+0x21b0+index*4)[0]
        assert actual == (meta['code']+target if target else 0), (index, hex(actual))
    # The profiler starts at a field boundary after the snapshot. Do not infer
    # its first tick from metadata: one or more updates may already have run.
    # Observe the scheduler's clear/set instructions, verified in this build.
    body = slave[32:32+size]
    gate_clear, gate_set = gate_sites(body, offsets)
    trace = barto.load(folder/'trace.bin')
    gate = None
    active = None
    updates = []
    generic = None
    # Observe native type-8/9/10 decisions and real projectile creation. These
    # instruction boundaries read type, write owner, and return a spawn result.
    for offset, expected in ((0xf13c, '302b0002'), (0xf6ec, '254b006a'),
                             (0xf630, '5c4f'), (0xf190, '4e75'),
                             (0xf81c, '102b0059'), (0xf86e, '5c4f'),
                             (0xf8e4, '5c4f'),
                             (0xf912, '5c4f')):
        at = meta['code']-meta['base']+offset
        assert memory[at:at+len(bytes.fromhex(expected))] == bytes.fromhex(expected)
    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            if generic is not None:
                if pc == meta['code']+0xf140:
                    generic['type'] = regs[0] & 0xffff
                    active['firing']['type_'+str(generic['type'])+'_decisions'] += 1
                elif pc == meta['code']+0xf820:
                    assert generic.get('type') == 10, 'type-10 handler for another actor type'
                    active['firing']['type_10_state_'+str(regs[0] & 0xff)+'_decisions'] += 1
                elif pc == meta['code']+0xf5e0:
                    active['firing']['cooldown_helper_calls'] += 1
                elif pc == meta['code']+0xf646:
                    active['firing']['spawn_attempts'] += 1
                elif pc == meta['code']+0xf6ec:
                    assert regs[11] == generic['actor'], 'projectile owner changed'
                    generic['owned'].add(regs[10])
                elif pc in (meta['code']+0xf630, meta['code']+0xf86e,
                            meta['code']+0xf8e4, meta['code']+0xf912):
                    # Type 10 calls the allocator directly at three sites instead
                    # of using the type-8/9 cooldown helper's return at $f630.
                    if pc != meta['code']+0xf630:
                        assert generic.get('type') == 10
                        active['firing']['type_10_spawn_returns'] += 1
                        active['firing'][f'type_10_return_{pc-meta["code"]:x}'] += 1
                    if regs[0]:
                        assert regs[0] in generic['owned'], 'spawn returned without owner write'
                        active['firing']['successful_spawns'] += 1
                    else:
                        active['firing']['failed_spawns'] += 1
                elif pc == meta['code']+0xf190:
                    generic = None
            if pc == base+gate_clear:
                gate = False
            elif pc == base+gate_set:
                gate = True
            elif pc == base+offsets['s60_update']:
                assert active is None, 'overlapping simulation updates'
                assert gate is not None, 'missing scheduler gate before update'
                active = dict(due=gate, offered=[], executed=[], callbacks=[], firing=collections.Counter())
            elif pc == base+offsets['s60_loop_complete']:
                if active is not None:
                    assert generic is None, 'generic callback did not return'
                    expected = active['offered'] if active['due'] else []
                    assert active['executed'] == expected, {
                        'update_index': len(updates), 'due': active['due'],
                        'expected': expected, 'executed': active['executed']}
                    updates.append(active)
                    active = None
            elif active is not None and pc == base+offsets['s60_ai']:
                callback = regs[9]-meta['code']
                active['callbacks'].append(callback)
                if callback in (0xeec4, 0xf136):
                    active['offered'].append((regs[11], callback))
            elif active is not None and pc in (meta['code']+0xeec4, meta['code']+0xf136):
                active['executed'].append((regs[11], pc-meta['code']))
                if pc == meta['code']+0xf136:
                    assert active['due'], 'generic callback outside decision tick'
                    assert generic is None, 'nested generic callback'
                    generic = dict(actor=regs[11], owned=set())
    firing = sum((update['firing'] for update in updates), collections.Counter())
    offered = [item for update in updates for item in update['offered']]
    executed = [item for update in updates for item in update['executed']]
    callbacks = collections.Counter(item for update in updates for item in update['callbacks'])
    due_indices = [i for i, update in enumerate(updates) if update['due']]
    assert updates and offered and executed, 'insufficient generic AI coverage'
    assert len(due_indices) >= 2, 'need at least two decision boundaries'
    assert all(b-a == n for a, b in zip(due_indices, due_indices[1:])), due_indices
    return dict(complete_updates=len(updates), incomplete_at_end=active is not None,
                offered_callbacks={hex(k): v for k, v in sorted(callbacks.items())},
                generic_offers=len(offered), generic_calls=len(executed),
                generic_actors=len({actor for actor, callback in offered}),
                decision_update_indices=due_indices,
                native_f136_firing_observations=dict(sorted(firing.items())),
                tick_substeps=n, matches_shared_decision_gate_and_actor_order=True)



if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--listing', required=True, type=Path)
    args = p.parse_args()
    print(json.dumps(inspect(args.capture, args.listing), indent=2, sort_keys=True))
