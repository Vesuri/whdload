#!/usr/bin/env python3
"""Audit the observed radar flag save/restore lifecycle in a retained trace.

This verifies complete radar passes, not all possible consumers of actor byte 1.
It deliberately does not normalize simulation-state comparisons.
"""
import argparse
import json
import re
from pathlib import Path
import barto


def inspect(folder):
    folder = Path(folder)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    code = meta['code']
    for offset, expected in ((0xbf8a, '4e55fff0'), (0xbfe2, '17530001'),
                             (0xbfe6, '16bc0088'), (0xc0d2, '16ab0001'),
                             (0xc0e0, '4279')):
        expected = bytes.fromhex(expected)
        at = code-meta['base']+offset
        assert memory[at:at+len(expected)] == expected, f'changed radar instruction {offset:x}'
    # Direct +1 reads whose surrounding code uses different structures:
    # level text, camera configuration, graphics records and sound data.
    # Report observed aliasing with actor addresses, rather than assuming it.
    other_reads = {0x8e08: 11, 0x129d0: 11, 0x135c6: 11, 0x136cc: 11,
                   0x13ce8: 11, 0x13d16: 11, 0x14b0a: 11, 0x1c788: 10}
    for offset, register in other_reads.items():
        expected = bytes.fromhex('102b0001' if register == 11 else '102a0001')
        at = code-meta['base']+offset
        assert memory[at:at+4] == expected, f'changed byte-1 read {offset:x}'
    actors, reads = set(), []
    active = None
    result = dict(complete_passes=0, saved_actors=0, restored_actors=0,
                  leading_partial_events=0)
    for field in (trace := barto.load(folder/'trace.bin')).fields:
        for pc, cost, regs in trace.instructions(field):
            offset = pc-code if pc is not None else None
            if offset in other_reads:
                reads.append((offset, regs[other_reads[offset]]))
            if offset == 0xbf8a:
                assert active is None, 'nested or unfinished radar pass'
                active = dict(saved=[], temporary=[], restored=[])
            elif offset in (0xbfe2, 0xbfe6, 0xc0d2):
                if active is None:
                    result['leading_partial_events'] += 1
                    continue
                name = {0xbfe2: 'saved', 0xbfe6: 'temporary', 0xc0d2: 'restored'}[offset]
                active[name].append(regs[11])
                actors.add(regs[11])
                if name == 'temporary':
                    assert active['temporary'] == active['saved'], 'temporary flags before matching save'
                if name == 'restored':
                    assert active['temporary'] == active['saved'], 'incomplete flag setup'
                    assert active['restored'] == active['saved'][:len(active['restored'])], 'restore order differs'
            elif offset == 0xc0e0 and active is not None:
                assert active['saved'] == active['temporary'] == active['restored'], active
                assert len(set(active['saved'])) == len(active['saved']), 'duplicate actors require separate restoration analysis'
                result['complete_passes'] += 1
                result['saved_actors'] += len(active['saved'])
                result['restored_actors'] += len(active['restored'])
                active = None
    result['other_direct_reads_observed'] = len(reads)
    result['other_direct_reads_aliasing_radar_actors'] = [hex(pc) for pc, pointer in reads if pointer in actors]
    result['partial_pass_at_end'] = active is not None
    assert result['complete_passes'], 'no complete radar pass in this trace'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture), indent=2))
