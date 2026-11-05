#!/usr/bin/env python3
"""Validate the observed S:0596 adjusted-return case against independent full traces."""
import argparse
import json
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from matrix_pc_check import check
from matrix_report import read_aprof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    result = check(args.control, args.candidate)
    before = read_aprof(args.control/'credits.aprof')[0]
    after = read_aprof(args.candidate/'credits.aprof')[0]
    meta = json.loads((args.candidate/'result.json').read_text())
    slave = meta['slave']
    snapshots = list(args.candidate.glob('calibration-*.bin'))
    memory = max(snapshots, key=lambda p: int(p.stem.split('-')[-1])).read_bytes()
    trace = barto.load(str(args.candidate/'credits.bin'))
    records = [r for f in trace.fields for r in trace.instructions(f) if r[0] not in (None, 0x7fffffff)]
    calls = 0
    for i, (pc, cost, regs) in enumerate(records):
        if pc != slave+0x596:
            continue
        call_pc = records[i-1][0]
        call = memory[call_pc-0x200000:call_pc-0x200000+6]
        if call[:2] != bytes.fromhex('4eb9') or int.from_bytes(call[2:], 'big') != pc:
            raise ValueError('unexpected call entry; fixture not covered')
        for j in range(i+1, len(records)-1):
            if records[j][0] == slave+0x5b6:
                if records[j][2][15] != regs[15]:
                    raise ValueError('return did not consume the original saved slot')
                if records[j+1][0] != call_pc+6+4 or records[j+1][2][15] != regs[15]+4:
                    raise ValueError('return address/stack adjustment differs')
                calls += 1
                break
        else:
            raise ValueError('missing observed return')
    if calls != 5 or after.get('adjusted_returns') != calls:
        raise ValueError('adjusted-return count mismatch')
    if before['unmatched_rts']-after['unmatched_rts'] != calls:
        raise ValueError('unexpected unmatched-return change')
    for key in ('units', 'gap', 'high', 'overflow', 'unmatched_rte', 'chip_units', 'chip_accesses'):
        if before[key] != after[key]:
            raise ValueError('unrelated aggregate changed: '+key)
    result.update(adjusted_return_cases=calls, stack_slot_case_checked=True,
                  remaining_contexts_validated=False)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
