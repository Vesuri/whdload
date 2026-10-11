#!/usr/bin/env python3
"""Check the native inactive-game branch and its SIM60 post-update path in a trace."""
import argparse
import collections
import json
import re
import struct
from pathlib import Path
import barto
from stellar7_report import locate


def inspect(folder, listing):
    folder, listing = Path(folder), Path(listing)
    slave = (folder/'slave.slave').read_bytes()
    assert slave == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    symbols = listing.read_text(encoding='latin1')
    names = ('s60_update', 's60_loop_complete', 's60_project',
             's60_stars_update', 's60_shake_update', 's60_cooldowns_update')
    offsets = {name: int(re.search(r'^'+name+r'\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
               for name in names}
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', slave, 28)[0]*4
    base = locate(memory, slave[32:32+size], meta['base'], header=32)
    assert base is not None
    code = meta['code']
    at = code-meta['base']
    assert memory[at+0x2b54:at+0x2b58] == bytes.fromhex('670000fa')
    assert memory[at+0x2c50:at+0x2c52] == bytes.fromhex('4e75')
    entries = {base+offsets[name]: name for name in names[2:]}
    entries.update({code+offset: name for offset, name in
                    ((0x3dc4, 'clone_timer'), (0xecca, 'power_timers'),
                     (0x2c58, 'post_update'), (0x3ab8, 'recenter'))})
    trace = barto.load(folder/'trace.bin')
    active = None
    completed = 0
    exits = []
    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            if pc is None or pc == 0x7fffffff:
                continue
            if pc == base+offsets['s60_update']:
                assert active is None, 'overlapping updates'
                active = dict(inactive=False, native_bypass=0, calls=collections.Counter())
            elif pc == base+offsets['s60_loop_complete']:
                if active is not None:
                    completed += 1
                    if active['inactive']:
                        exits.append(dict(native_bypass=active['native_bypass'],
                                          calls=dict(sorted(active['calls'].items()))))
                    active = None
            elif active is not None:
                if active.get('branch_sp') == regs[15]:
                    # Follow the actual BEQ destination, tolerating an interrupt
                    # between branch and target without relying on SR sampling.
                    assert pc in (code+0x2b58, code+0x2c50), ('branch target', hex(pc))
                    active['inactive'] = pc == code+0x2c50
                    del active['branch_sp']
                if pc == code+0x2b54:
                    active['branch_sp'] = regs[15]
                if active['inactive']:
                    if pc == code+0x2c50:
                        active['native_bypass'] += 1
                    if pc in entries:
                        active['calls'][entries[pc]] += 1
    return dict(complete_updates=completed, partial_at_end=active is not None,
                inactive_updates=exits)


def validate(result):
    assert result['inactive_updates'], 'no complete inactive-update path observed'
    for update in result['inactive_updates']:
        assert update['native_bypass'] == 1, update
        for forbidden in ('s60_project', 's60_stars_update', 's60_shake_update'):
            assert not update['calls'].get(forbidden), ('inactive callback', forbidden, update)
        for required in ('s60_cooldowns_update', 'clone_timer', 'power_timers',
                         'post_update', 'recenter'):
            assert update['calls'].get(required) == 1, ('post-update count', required, update)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', required=True, type=Path)
    args = parser.parse_args()
    result = inspect(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)
