#!/usr/bin/env python3
"""Validate observed polygon interrupt batching in an exact-build trace.

Checks native ownership/call order, the saved BLIT enable bit, absence of BLIT
interrupts while masked, and callee-saved registers/stack at return. Partial
windows and unrelated events are counted separately. This is observed-path
coverage, not a proof of every possible graphics-library or interrupt caller.
"""
import argparse
import json
import re
import struct
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from audit_hooks import installed
from stellar7_report import locate, regions


def validate(events):
    phase = None
    completed = enabled = disabled = unscoped = 0
    callee = bit = None
    for event, registers in events:
        if event == 'own':
            assert phase is None, ('nested ownership', phase)
            phase = 'own'
        elif phase is None:
            unscoped += 1
        elif event == 'call':
            assert phase == 'own', phase
            callee = (*registers[2:8], *registers[10:16])
            phase = 'call'
        elif event == 'wait':
            assert phase == 'call', phase
            phase = 'wait'
        elif event == 'mask':
            assert phase == 'wait', phase
            bit = registers[0] & 0xffff
            assert bit in (0, 0x40)
            phase = 'masked'
        elif event == 'polygon':
            assert phase == 'masked', phase
            phase = 'drawing'
        elif event == 'restore':
            assert phase == 'drawing', phase
            assert registers[0] & 0xffff == (0x8000 | bit), 'wrong restored interrupt enable'
            phase = 'restored'
        elif event == 'disown':
            assert phase == 'restored', phase
            assert callee == (*registers[2:8], *registers[10:16]), 'caller registers/stack changed'
            completed += 1
            enabled += bit == 0x40
            disabled += bit == 0
            phase = None
        elif event == 'blitter-irq':
            assert phase not in ('masked', 'drawing'), 'blitter interrupt in masked window'
    assert completed, 'no complete owned polygons'
    return dict(completed=completed, enabled_on_entry=enabled,
                disabled_on_entry=disabled, unscoped_events=unscoped,
                incomplete=phase)


def inspect(folder, listing):
    folder, listing = Path(folder), Path(listing)
    hooks = installed(folder, listing)
    binary = (folder/'slave.slave').read_bytes()
    symbols = {name: int(value, 16) for name, value in re.findall(
        r'^(\w+)\s+00:([0-9A-F]+)', listing.read_text(encoding='latin1'), re.M)}
    assert 's60_polygon_mask' in symbols, 'build has no polygon interrupt batching'
    meta = {key: int(value, 0) for key, value in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', binary, 28)[0]*4
    body = binary[32:32+size]
    slave = locate(memory, body, meta['base'], header=32)
    assert slave is not None
    for name, encoded in [('s60_polygon_mask', '33fc004000dff09a'),
                          ('s60_polygon_restore', '33c000dff09a')]:
        offset = symbols[name]
        expected = bytes.fromhex(encoded)
        assert body[offset:offset+len(expected)] == expected, 'unexpected interrupt write'
    trace = barto.load(folder/'trace.bin')
    kick = next(origin for lo, hi, name, origin in regions(memory, meta['base'], trace.chip)
                if name == 'kick')
    sites = {meta['code']+0x14c56: 'own', meta['code']+0x14c5c: 'call',
             meta['code']+0x2510c: 'wait', meta['code']+0x17e88: 'polygon',
             meta['code']+0x14c62: 'disown',
             slave+symbols['s60_polygon_mask']: 'mask',
             slave+symbols['s60_polygon_restore']: 'restore',
             kick+0xfc0d38: 'blitter-irq'}
    events = ((sites[pc], tuple(registers)) for field in trace.fields
              for pc, cost, registers in trace.instructions(field) if pc in sites)
    return dict(**validate(events), hooks=hooks, scope=__doc__)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture, args.listing), indent=2))
