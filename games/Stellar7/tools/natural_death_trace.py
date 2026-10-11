#!/usr/bin/env python3
"""Verify an observed negative-energy death leaves SIM60 for native cleanup.

Requires a complete transition in the trace. Does not validate the subsequent
Continue answer, retry, or new-game path.
"""
import argparse
import json
import re
import struct
from pathlib import Path
import barto
from stellar7_report import locate


def validate(events):
    deaths = [i for i, e in enumerate(events) if e['event'] == 'negative_energy']
    assert len(deaths) == 1, ('expected one negative-energy transition', len(deaths))
    transition = events[deaths[0]:]
    expected = ('negative_energy', 'clear_active', 'mark_death', 'complete_update',
                'exit_simulation', 'restore_input', 'native_cleanup', 'native_death_path')
    observed = tuple(e['event'] for e in transition)
    assert observed == expected, ('death transition order or post-exit work', observed)
    assert -32768 <= transition[0]['energy'] < 0, 'death requires negative native energy'
    return dict(energy=transition[0]['energy'],
                first_field=transition[0]['field'], last_field=transition[-1]['field'],
                events=transition, scope='Native death entry and simulation exit only; Continue/retry unverified')


def inspect(folder, listing):
    folder, listing = Path(folder), Path(listing)
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    symbols = listing.read_text(encoding='latin1')
    names = {'s60_update': 'update', 's60_render': 'simulation_render',
             's60_loop_complete': 'complete_update', 's60_loop_exit': 'exit_simulation',
             's60_input_restore': 'restore_input'}
    offsets = {name: int(re.search(r'^'+name+r'\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
               for name in names}
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|data|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', binary, 28)[0]*4
    base = locate(memory, binary[32:32+size], meta['base'], header=32)
    assert base is not None, 'retained slave is absent from captured memory'
    code, data = meta['code'], meta['data']
    native = code-meta['base']
    def guard(offset, value):
        assert memory[native+offset:native+offset+len(value)] == value, ('native guard', hex(offset))
    # Guard source energy and both native stores, including their relocations.
    guard(0x2cce, bytes.fromhex('3039')+struct.pack('>I', data+0x46c4))
    guard(0x2cd4, bytes.fromhex('4a406a0e'))
    guard(0x2cd8, bytes.fromhex('4239')+struct.pack('>I', data+0x1e53))
    guard(0x2cde, bytes.fromhex('700133c0')+struct.pack('>I', data+0x1e90))
    guard(0x2d7c, bytes.fromhex('610003ca'))
    guard(0x2d88, bytes.fromhex('4a79')+struct.pack('>I', data+0x1e90)+bytes.fromhex('675a'))
    guard(0x2d90, bytes.fromhex('4279')+struct.pack('>I', data+0x1e9c))
    entries = {base+offsets[name]: event for name, event in names.items()}
    entries.update({code+offset: event for offset, event in
                    ((0x2cd8, 'clear_active'), (0x2ce0, 'mark_death'),
                     (0x2d7c, 'native_cleanup'), (0x2d90, 'native_death_path'))})
    events = []
    trace = barto.load(folder/'trace.bin')
    for index, field in enumerate(trace.fields):
        for pc, cost, regs in trace.instructions(field):
            if pc == code+0x2cd6:
                energy = regs[0] & 0xffff
                if energy & 0x8000:
                    events.append(dict(event='negative_energy', energy=energy-0x10000, field=index))
            if pc in entries:
                events.append(dict(event=entries[pc], field=index))
    return dict(fields=len(trace.fields), events=events)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.capture, args.listing)
    print(json.dumps(validate(result['events']), indent=2))
