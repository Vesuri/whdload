#!/usr/bin/env python3
"""Audit whole-pass projection callback ordering in an exact-build trace."""
import argparse
import json
import re
import struct
from pathlib import Path
import barto
from stellar7_report import locate


def inspect(folder, listing):
    folder, listing = Path(folder), Path(listing)
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    source = listing.read_text(encoding='latin1').split('Source: "project_batch60.s"')[1].split('Source: "sim60.s"')[0]
    instructions = []
    for offset, encoded, text in re.findall(r'^00:([0-9A-F]+)\s+([0-9A-F]+)\s+\d+:\s*(.*)$', source, re.M):
        offset = int(offset, 16)
        code = bytes.fromhex(encoded)
        assert binary[32+offset:32+offset+len(code)] == code, 'listing opcode mismatch'
        instructions.append((offset, text.split(';')[0].strip()))

    def point(text, occurrence=0):
        matches = [offset for offset, line in instructions if line == text]
        assert len(matches) > occurrence, text
        return matches[occurrence]

    # Observe registers after loads, before the instruction at each point.
    points = {point('movem.l d1-d7/a0-a6,-(sp)'): 'entry',
              point('cmpa.l a6,a3'): 'actor',
              point('beq .guard_next', 1): 'callback',
              point('jsr (a5)'): 'call',
              point('moveq #1,d0'): 'accept',
              point('moveq #0,d0'): 'fallback'}
    meta = {key: int(value, 0) for key, value in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    size = struct.unpack_from('>I', binary, 28)[0]*4
    base = locate((folder/'code.bin').read_bytes(), binary[32:32+size], meta['base'], header=32)
    assert base is not None
    points = {base+offset: name for offset, name in points.items()}
    current = None
    result = dict(accepted_complete_passes=0, fallback_passes=0, ordered_callbacks=0)
    for field in (trace := barto.load(folder/'trace.bin')).fields:
        for pc, cost, regs in trace.instructions(field):
            event = points.get(pc)
            if event == 'entry':
                assert current is None, 'nested projection pass'
                current = dict(actors=[], expected=[], actual=[])
            elif current is not None:
                if event == 'actor':
                    current['actors'].append(regs[11])
                    current['count'] = regs[7] & 65535
                elif event == 'callback' and regs[0]:
                    current['expected'].append((len(current['actors'])-1, regs[11], regs[0]))
                elif event == 'call':
                    current['actual'].append((regs[6] & 65535, regs[11], regs[13]))
                elif event == 'accept':
                    assert len(current['actors']) == current['count']
                    assert current['expected'] == current['actual'], current
                    assert all(target == meta['code']+0x42b0 for _, _, target in current['actual'])
                    result['accepted_complete_passes'] += 1
                    result['ordered_callbacks'] += len(current['actual'])
                    current = None
                elif event == 'fallback':
                    assert not current['actual'], 'callback executed before fallback'
                    result['fallback_passes'] += 1
                    current = None
    result['partial_pass_at_end'] = current is not None
    assert result['accepted_complete_passes'] + result['fallback_passes'], 'no complete passes'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture, args.listing), indent=2))
