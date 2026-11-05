#!/usr/bin/env python3
"""Read and validate the five-pilot linked list in a human qualifying/race dump.

Use --sorted only at a known native sorting completion checkpoint. A generic
end-of-window dump can stop between movement and sorting. This is structural
and native-comparison validation, not proof of equal-time racing trajectories.
"""
import argparse
from pathlib import Path
import struct


def signed(word):
    return word - 65536 if word & 32768 else word


def inspect(chip, game, require_sorted=False):
    state = game + 0xa6e
    def word(at):
        return struct.unpack_from('>H', chip, at)[0]
    def long(at):
        return struct.unpack_from('>I', chip, at)[0]
    assert word(state + 0xb6) == word(state + 0xbe) == 0, 'Not an ordinary human race/qualifying bank'
    assert word(state + 0x340) == 3 and long(state + 0x342) == game + 0x1ab0
    expected = {0x11c: 0, **{0x1042 + i * 190: i + 1 for i in range(4)}}
    head = long(state + 0x33c)
    current, previous = head, 0
    nodes = []
    seen = set()
    while current:
        assert current in expected and current not in seen, 'Unknown/cyclic pilot link'
        seen.add(current)
        at = state + current
        assert at + 190 <= len(chip)
        identity = word(at)
        assert identity == expected[current], 'Record address/id disagreement'
        assert long(at + 0x28) == previous, 'Broken previous-pilot link'
        node = dict(id=identity, offset=current, lap=signed(word(at + 0x22)),
                    segment=signed(word(at + 2)), repair=word(at + 0x56))
        nodes.append(node)
        previous, current = current, long(at + 0x2c)
    assert seen == set(expected), 'Pilot missing from native list'
    if require_sorted:
        repair_segment = word(state + 0x280)
        for a, b in zip(nodes, nodes[1:]):
            # Reproduce the actual F5D0..F5FC word arithmetic, including F5F2
            # adding the second pilot repair value to D0 rather than D1.
            left = ((a['lap'] << 8) + (repair_segment if a['repair'] else a['segment'])) & 65535
            right = (b['lap'] << 8) & 65535
            if b['repair']:
                left = (left + repair_segment) & 65535
            else:
                right = (right + b['segment']) & 65535
            assert signed(left) >= signed(right), 'Native comparator would still exchange adjacent pilots'
    return dict(qualifying=bool(word(state + 0xc0)), nodes=nodes)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures', type=Path, nargs='+')
    p.add_argument('--snapshot', default='final-chip.bin')
    p.add_argument('--sorted', action='store_true', dest='require_sorted')
    args = p.parse_args()
    for root in args.captures:
        game = int((root / 'game-base.txt').read_text(), 0)
        result = inspect((root / args.snapshot).read_bytes(), game, args.require_sorted)
        print(f'{root.name}: {"qualifying" if result["qualifying"] else "race"}; five complete reciprocal pilot links')
        print('  Order (id: lap/segment): ' + ', '.join(f'{n["id"]}: {n["lap"]}/{n["segment"]}' for n in result['nodes']))
