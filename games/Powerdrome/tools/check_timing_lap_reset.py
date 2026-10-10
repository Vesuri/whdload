#!/usr/bin/env python3
"""Check the natural countdown reset and subsequent logical opponent lap reads.

Capture starts at DBD8 with DBDE/DBE8/DBEE/DBF4/CEDC/D7FE/D86C probes.
This does not validate player result duration or unrelated reset entry paths.
"""
import argparse
from pathlib import Path
import struct
from check_timing_retune import events


def u32(data, offset):
    return struct.unpack_from('>I', data, offset)[0]


def check(root):
    game = int((root/'game-base.txt').read_text(), 0)
    base = int((root/'dump-base.txt').read_text(), 0)
    chip = (root/'chip.bin').read_bytes()
    before = (root/'code.bin').read_bytes()
    after = (root/'final-code.bin').read_bytes()
    frame = u32(chip, game+0xca46)-base
    lap = before.find(b'PDLAP001', frame, frame+16384)
    assert lap >= 0
    state = game+0xa6e
    assert struct.unpack_from('>h', chip, state+0x43a)[0] == 7
    native = u32(chip, state+0x206)
    rows = events(root)
    resets = [r for r in rows if r['off'] == 0xdbde]
    assert len(resets) == 1, 'Need exactly one countdown reset'
    reset = resets[0]
    session, opponent = reset['PDSESSION_EVENT'], reset['PDPOPP_EVENT']
    assert session[8] == opponent[0] == 1
    clock, origin = session[14], opponent[13]
    elapsed = (clock-origin+18) & 0xffffffff
    old_epoch = u32(before, lap+8)
    expected = (native-elapsed) & 0xffffffff
    print(f'{root.name}: reset logical elapsed {elapsed*5} ms; old lap clock differs from native reset by {(native-old_epoch-elapsed)*5} ms')
    assert u32(after, lap+24) == u32(before, lap+24)+1, 'Reset hook did not rebase exactly once'
    assert (u32(after, lap+8), u32(after, lap+28), u32(after, lap+32), u32(after, lap+36)) == (expected, clock, native, old_epoch)
    assert sum(r['off'] == 0xdbe8 for r in rows) == 5
    assert sum(r['off'] == 0xdbee for r in rows) == 5
    first = next(r for r in rows if r['off'] == 0xcedc)
    assert len(first['arrays']) == 4
    assert all(u32(record, 0x5c) == native for record in first['arrays']), 'Native opponent reset values changed'
    reads = []
    for row in rows:
        if row['off'] not in (0xd7fe, 0xd86c):
            continue
        opponent = row['PDPOPP_EVENT']
        assert opponent[1] == 1 and opponent[13] == origin
        value = (expected+opponent[5]-origin+18) & 0xffffffff
        assert opponent[20] == value, 'Lap read is outside the rebased logical domain'
        reads.append(row['off'])
    assert reads.count(0xd7fe) >= 4 and reads.count(0xd86c) >= 4, 'Need four minimum-interval and four completed-lap reads'
    print(f'  One rebase, five native reset visits, four unchanged opponent stamps; {len(reads)} logical lap reads pass')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    check(parser.parse_args().capture)
