#!/usr/bin/env python3
"""Check native heading results and division operands in a retained trace.

This models the ordinary non-overflow arctangent-table path. Unmodeled signed
extremes are reported, not silently treated as verified. This is a candidate
optimization audit, not a replacement for native-reference boundary fixtures.
"""
import argparse
import collections
import json
import struct
from pathlib import Path
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto
from routine_cost import measure


def inspect(folder):
    folder = Path(folder)
    meta = json.loads((folder/'metadata.json').read_text())
    memory = (folder/'code.bin').read_bytes()
    code, data = meta['code_base'], meta['data_base']
    table = struct.unpack_from('>513H', memory, data-meta['base']+0xa60)
    counts = collections.Counter()
    pending = None
    for field in (trace := barto.load(folder/'trace.bin')).fields:
        for pc, cost, regs in trace.instructions(field):
            if pc == code+0x894a:
                assert pending is None, 'overlapping heading calls'
                x, z = (v if v < 0x80000000 else v-0x100000000 for v in (regs[7], regs[6]))
                a, b = abs(x), abs(z)
                # Larger operands can exercise wrapped negation/shift and
                # signed table indexing; those need the original fallback.
                if max(a, b) >= 0x80000000 or min(a, b) > 0x3fffff:
                    pending = ('unmodeled', None)
                    continue
                if a == 0:
                    angle = 1024
                elif b == 0:
                    angle = 0
                elif a == b:
                    angle = 512
                elif a < b:
                    angle = 1024-table[(a*512)//b]
                else:
                    angle = table[(b*512)//a]
                if x < 0:
                    angle = 2048-angle
                if z < 0:
                    angle = 4096-angle
                pending = ('modeled', ((angle-1024)*16) & 0xffff)
            elif pc == code+0x8a08 and pending is not None:
                kind, expected = pending
                if kind == 'modeled':
                    assert regs[0] & 0xffff == expected, (expected, regs[0] & 0xffff)
                counts[kind+'_results'] += 1
                pending = None
            elif pc == code+0x8a74:
                n, d = regs[:2]
                counts['division_calls'] += 1
                if n < 0x80000000 and 0 < d <= 65535 and n//d <= 65535:
                    counts['positive_single_divu'] += 1
                else:
                    counts['division_requires_fallback'] += 1
    assert counts['modeled_results'], 'no complete modeled heading calls'
    result = dict(coverage=dict(counts), incomplete_at_end=pending is not None)
    for name, offset in (('heading', 0x893a), ('division', 0x8a74)):
        result[name] = measure(folder, offset)
        result[name].pop('samples')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture), indent=2, sort_keys=True))
