#!/usr/bin/env python3
"""Audit observed stack returns into native patch ranges.

Matches each executed native/slave RTS, RTR or RTD to the next trace record
and checks the stack adjustment. A profiler gap may be bridged only when
its saved registers equal the following instruction snapshot and preserve
the return register/stack transition. Other boundaries remain unverified;
no return address is inferred from stale SR or snapshot stack contents. Exception returns and unseen paths remain outside scope.
"""
import argparse
import collections
import json
import re
import struct
from pathlib import Path
import audit_hooks
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
from amigaxdev.patchlist import slave_code
from stellar7_report import locate


def inspect(folder, listing, trace=None):
    folder, listing = Path(folder), Path(listing)
    installation = audit_hooks.installed(folder, listing)
    static = audit_hooks.audit(listing)
    interiors, padding = set(), set()
    for group in static['ranges']:
        start, end = int(group['start'], 16), int(group['end'], 16)
        entries = {p['start'] for p in group['patches'] if p['command'] != 'NOP'} | {start}
        interiors.update(set(range(start, end))-entries)
        for patch in group['patches']:
            if patch['command'] == 'NOP':
                padding.update(range(patch['start'], patch['end'], 2))
            elif patch['command'] == 'PSS':
                padding.update(range(patch['start']+6, patch['end'], 2))
    meta = {k: int(v, 0) for k, v in re.findall(r'^(code|base)=(\S+)',
                 (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    body = slave_code(folder/'slave.slave')
    slave = locate(memory, body, meta['base'], header=32)
    assert slave is not None
    code = meta['code']
    for offset in padding:
        assert memory[code-meta['base']+offset:code-meta['base']+offset+2] == bytes.fromhex('4e71')
    def label(pc):
        if code <= pc < code+0x25360:
            return f'native:{pc-code:#x}'
        if slave <= pc < slave+len(body):
            return f'slave:{pc-slave:#x}'
        return 'external'
    pending = None
    gap_regs = None
    bridged = 0
    counts = collections.Counter()
    excluded = collections.Counter()
    padding_counts = collections.Counter()
    decoded = {}
    observed = 0
    trace = trace or barto.load(folder/'trace.bin')
    for field in trace.fields:
        for pc, _, regs in trace.instructions(field):
            if pending is not None:
                origin, instruction, expected_sp, before = pending
                if pc == 0x7fffffff and gap_regs is None:
                    gap_regs = tuple(regs)
                    continue
                if gap_regs is not None:
                    assert pc != 0x7fffffff, 'consecutive gap records after return'
                    assert tuple(regs) == gap_regs, 'gap/instruction register snapshots differ'
                if pc is None:
                    excluded['missing_pc_boundary'] += 1
                elif gap_regs is not None and (regs[15] != expected_sp or tuple(regs[:15]) != before):
                    excluded['gap_register_discontinuity'] += 1
                else:
                    assert regs[15] == expected_sp, f'unverified return stack transition from {origin}'
                    offset = pc-code
                    assert offset not in interiors or offset in padding, f'return enters native patch operand/interior at {offset:#x}'
                    counts[(origin, label(pc), instruction)] += 1
                    bridged += int(gap_regs is not None)
                    if offset in interiors and offset in padding:
                        padding_counts[hex(offset)] += 1
                pending = None
                gap_regs = None
            if pc is None or pc == 0x7fffffff or label(pc) == 'external':
                continue
            if pc not in decoded:
                at = pc-meta['base']
                word, = struct.unpack_from('>H', memory, at)
                decoded[pc] = ('RTS', 4) if word == 0x4e75 else ('RTR', 6) if word == 0x4e77 else ('RTD', 4+struct.unpack_from('>h', memory, at+2)[0]) if word == 0x4e74 else None
            if decoded[pc] is not None:
                instruction, adjustment = decoded[pc]
                pending = label(pc), instruction, (regs[15]+adjustment) & 0xffffffff, tuple(regs[:15])
                observed += 1
    if pending is not None:
        excluded['trailing_return'] += 1
    assert counts, 'no verified returns in trace'
    assert observed == sum(counts.values())+sum(excluded.values())
    return dict(installation=installation, observed_returns=observed,
                verified_returns=sum(counts.values()), gap_bridged_returns=bridged, unverified=dict(excluded),
                declared_padding_returns=dict(padding_counts),
                destinations=[dict(source=s, target=t, instruction=i, executions=n)
                              for (s, t, i), n in sorted(counts.items())],
                scope='Observed RTS/RTR/RTD transitions from native game/slave, with matching stack adjustment; gaps require identical gap/next-instruction snapshots and preserved D0-D7/A0-A6. Only declared installed NOP padding is allowed inside a patch. Excludes discontinuous/missing-PC/trailing returns, exception returns, external-source returns, unseen paths and full replacement semantics.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture, args.listing), indent=2))
