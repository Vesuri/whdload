#!/usr/bin/env python3
"""Audit trace-register indirect JSR/JMP targets against compiled patch interiors.

Covers executed address-register and brief-indexed calls/jumps in native code
and the exact loaded slave. Returns, exception vectors, unobserved paths and
replacement semantics are outside this check. No whole-program safety claim.
"""
import argparse
import collections
import json
import re
import struct
from pathlib import Path
import audit_hooks
import barto
from patchlist import slave_code
from stellar7_report import locate


def signed(value, bits):
    value &= (1 << bits)-1
    return value-(1 << bits) if value & (1 << (bits-1)) else value


def target(word, extension, pc, regs):
    """68000 address-register or brief-indexed effective address."""
    mode, register = (word >> 3) & 7, word & 7
    if mode == 2:
        return regs[8+register]
    if mode == 5:
        return (regs[8+register]+signed(extension, 16)) & 0xffffffff
    assert mode == 6 or (mode == 7 and register == 3), 'unsupported indirect mode'
    assert not extension & 0x100, 'full-format indexed extension requires separate audit'
    index = regs[(extension >> 12) & 15]
    index = signed(index, 32 if extension & 0x800 else 16)
    index *= 1 << ((extension >> 9) & 3)
    base = regs[8+register] if mode == 6 else pc+2
    return (base+index+signed(extension, 8)) & 0xffffffff


def inspect(folder, listing, trace=None):
    folder, listing = Path(folder), Path(listing)
    installation = audit_hooks.installed(folder, listing)
    static = audit_hooks.audit(listing)
    interiors = set()
    for group in static['ranges']:
        start, end = int(group['start'], 16), int(group['end'], 16)
        entries = {p['start'] for p in group['patches'] if p['command'] != 'NOP'} | {start}
        interiors.update(set(range(start, end))-entries)
    meta = {k:int(v, 0) for k,v in re.findall(r'^(code|base)=(\S+)',
                                             (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    body = slave_code(folder/'slave.slave')
    slave = locate(memory, body, meta['base'], header=32)
    assert slave is not None
    code = meta['code']
    counts = collections.Counter()
    decoded = {}
    for field in (trace := trace or barto.load(folder/'trace.bin')).fields:
        for pc, _, regs in trace.instructions(field):
            if pc is None or not (code <= pc < code+0x25360 or slave <= pc < slave+len(body)):
                continue
            if pc not in decoded:
                at = pc-meta['base']
                word, extension = struct.unpack_from('>HH', memory, at)
                mode, register = (word >> 3) & 7, word & 7
                indirect = word & 0xffc0 in (0x4e80, 0x4ec0) and (mode in (2, 5, 6) or (mode == 7 and register == 3))
                decoded[pc] = (word, extension) if indirect else None
            if decoded[pc] is None:
                continue
            word, extension = decoded[pc]
            destination = target(word, extension, pc, regs)
            assert destination-code not in interiors, f'indirect patch-interior target at native {destination-code:#x}'
            origin = f'native:{pc-code:#x}' if code <= pc < code+0x25360 else f'slave:{pc-slave:#x}'
            dest = f'native:{destination-code:#x}' if code <= destination < code+0x25360 else f'slave:{destination-slave:#x}' if slave <= destination < slave+len(body) else 'external'
            counts[(origin, dest, 'JSR' if word & 0xffc0 == 0x4e80 else 'JMP')] += 1
    assert counts, 'no indirect calls/jumps in trace'
    return dict(installation=installation, indirect_executions=sum(counts.values()),
                source_sites=len({key[0] for key in counts}),
                destinations=[dict(source=s, target=t, instruction=i, executions=n)
                              for (s,t,i),n in sorted(counts.items())],
                scope='Targets computed from executed indirect JSR/JMP register operands in this trace. Excludes returns, exceptions, unseen paths and replacement semantics.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture, args.listing), indent=2))
