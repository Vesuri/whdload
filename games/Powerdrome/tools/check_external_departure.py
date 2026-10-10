#!/usr/bin/env python3
"""Measure the 17-position external pit animation and compare native geometry.

Capture from 1475C with TIMING_STATE=1, marker 1479E and probes 14764/147A6.
The reference should be an A500 capture with CUSTOM3=0. Without candidates this
reports calibration only; it does not certify elapsed-time pacing.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import struct


def inspect(root):
    cfg = json.loads((root / 'configuration.json').read_text())
    assert int(cfg['ANCHOR'], 0) == 0x1475c
    assert int(cfg['SWAP_MARKER'], 0) == 0x1479e
    game = int((root / 'game-base.txt').read_text(), 0)
    chip = (root / 'chip.bin').read_bytes()
    final = (root / 'final-chip.bin').read_bytes()
    table = game + 0x144cc
    positions = struct.unpack_from('>17h', chip, table)
    assert chip[table:table+34] == final[table:table+34], 'Position table mutated'
    text = (root / 'swaps-gdb.txt').read_text()
    rows = [(int(field), int(off, 16), list(map(int, values.split())))
            for field, off, values in re.findall(
                r'^PDMREG_EVENT (-?\d+) (0x[0-9a-f]+) (.+)$', text, re.M)]
    steps = [(f, v) for f, off, v in rows if off == 0x14764]
    returns = [(f, v) for f, off, v in rows if off == 0x147a6]
    assert len(steps) == 17 and len(returns) == 1, 'Need exactly one complete animation'
    for index, (_, regs) in enumerate(steps):
        assert len(regs) == 19
        assert regs[7] & 65535 == 16-index, 'Wrong native DBRA sequence'
        assert regs[8] == table + 2*index, 'Wrong position-table progression'
        assert regs[15] == steps[0][1][15], 'Loop stack drift'
    assert returns[0][1][7] & 65535 == 65535
    assert returns[0][1][8] == table + 34
    assert returns[0][1][15] == steps[0][1][15], 'Return stack drift'
    fields = [f for f, _ in steps] + [returns[0][0]]
    intervals = [(b-a)*20 for a, b in zip(fields, fields[1:])]
    print(f'{root.name}: 17 native positions and stable stack; '
          f'{(fields[-2]-fields[0])*20} ms first-to-last, '
          f'{(fields[-1]-fields[0])*20} ms first-to-return')
    print(f'  Per-step PAL intervals (ms: count): {dict(sorted(Counter(intervals).items()))}')
    return positions, fields


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('captures', type=Path, nargs='*')
    args = parser.parse_args()
    config = json.loads((args.reference / 'configuration.json').read_text())
    assert config['CPU'] == '68000' and config['FAST_KB'] == '0'
    assert 'CUSTOM3=0' in config['WHD_ARGS'], 'Reference must disable timing corrections'
    positions, _ = inspect(args.reference)
    for capture in args.captures:
        actual, _ = inspect(capture)
        assert actual == positions, 'External departure geometry differs from reference'
