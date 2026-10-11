#!/usr/bin/env python3
"""Require opponent service and keyboard polling on each directed repair step.

Pairs native call boundaries inside all 264 repair steps, including dropped
presentations. Scheduling arithmetic is checked separately by the opponent-ledger
verifier. This does not prove key consumption, nonlocal exits or arbitrary modes.
"""
import argparse
from collections import Counter
from pathlib import Path


def check(root):
    assert (root / 'final-code.bin').is_file(), 'Capture must be terminal'
    active = None
    totals = Counter()
    polls = Counter()
    sites = (0xe3bc, 0xe3c4, 0xe3d0, 0xe3d6)
    for line in (root / 'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDTIME_EVENT' and active is not None:
            off = int(v[2], 16)
            if off in sites:
                active['sites'].append(off)
        if v[0] == 'PDPOPP_EVENT' and active is not None and int(v[2], 16) == 0xe3d6:
            registers = list(map(int, v[3:]))
            assert len(registers) == 27 and registers[19] in (0, 0xffffffff)
            polls['nonempty' if registers[19] else 'empty'] += 1
        if v[0] != 'PDRDROP_EVENT':
            continue
        off = int(v[2], 16)
        values = list(map(int, v[3:]))
        if off in (0x148d8, 0x14a20):
            assert active is None, 'Missing prior repair step completion'
            active = {'entry': off, 'dropped': values[0], 'sites': []}
            assert values[0] in (0, 1)
        elif off in (0x14962, 0x14aa6):
            assert active is not None, 'Missing repair step entry'
            assert (active['entry'], off) in ((0x148d8, 0x14962), (0x14a20, 0x14aa6))
            assert values[0] == 0, 'Drawing suppression leaked past service'
            assert active['sites'] == list(sites), (
                f'Step {sum(totals.values())+1}: expected one opponent call/return '
                f'and keyboard poll/return, got {active["sites"]}')
            totals['dropped' if active['dropped'] else 'drawn'] += 1
            active = None
    assert active is None and sum(totals.values()) == 264, 'Need all eight complete stages'
    assert totals['dropped'] and totals['drawn'], 'Need both presentation paths'
    assert sum(polls.values()) == 264, 'Missing native keyboard availability results'
    print(f'{root.name}: all 264 repair steps perform one native opponent service call and one keyboard poll')
    print(f'  {totals["drawn"]} drawn / {totals["dropped"]} dropped; call/return ordering and cleared suppression pass')
    print(f'  Native keyboard availability: {polls["empty"]} empty / {polls["nonempty"]} nonempty')
    print('  Input consumption, nonlocal exits, other branches and full opponent state remain separate')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    check(parser.parse_args().capture)
