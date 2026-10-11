#!/usr/bin/env python3
"""Check native lap-register results and continuous logical message deadlines.

Probe 10c16, 10c22 and 10c2a. --expect-native-rebase diagnoses the old
prototype. Debugger SR does not prove guest flags; those need a guest contract.
"""
import argparse
from pathlib import Path
from check_flight_message import read


def check(root, expect_native_rebase=False):
    pending = None
    rebased = None
    count = active = 0
    for row in read(root):
        off = row['off']
        if off == 0x10c16:
            assert pending is None and rebased is None
            domain = row['domain']
            assert len(domain) == 8 and len(row['PDMREG_EVENT']) == 19
            assert domain[:3] == [1, 0, 1] and domain[6:] == [0, 65535]
            pending = row
        elif off == 0x10c22:
            assert pending is not None
            old = pending['PDMESSAGE_EVENT']
            new = row['PDMESSAGE_EVENT']
            native = (old[1] - old[0]) & 0xffffffff
            assert old[0] != 0, 'Zero counter does not exercise rebasing'
            assert new[1] == (native if expect_native_rebase else old[1])
            assert old[0] == new[0] and old[2] == new[2]
            regs = pending['PDMREG_EVENT'][:]
            regs[1] = native
            after = row['PDMREG_EVENT']
            assert len(after) == 19
            assert regs[:16] == after[:16] and regs[17:] == after[17:]
            assert pending['domain'] == row['domain']
            rebased = row
        elif off == 0x10c2a:
            assert pending is not None and rebased is not None
            assert row['PDMESSAGE_EVENT'][0] == 0
            assert row['PDMESSAGE_EVENT'][1:3] == rebased['PDMESSAGE_EVENT'][1:3]
            before, after = rebased['PDMREG_EVENT'], row['PDMREG_EVENT']
            assert before[:16] == after[:16] and before[17:] == after[17:]
            assert row['domain'] == pending['domain']
            old = pending['PDMESSAGE_EVENT']
            phase = pending['domain'][3]
            live = pending['domain'][5] != 0 and old[1] > phase
            active += live
            print(f'  field {row["field"]}: phase={phase}, deadline={old[1]} -> {row["PDMESSAGE_EVENT"][1]}, native counter={old[0]}, live={live}')
            count += 1
            pending = rebased = None
    assert count and pending is None and rebased is None
    print(f'{root.name}: {count} lap rebases, {active} live deadlines; D/A/SP and native D1 subtraction verified')
    print('  Guest flags, phase wrap and other mode transitions remain separate checks')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--expect-native-rebase', action='store_true')
    a = p.parse_args()
    check(a.capture, a.expect_native_rebase)
