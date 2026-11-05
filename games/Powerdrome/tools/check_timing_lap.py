#!/usr/bin/env python3
"""Check stable opponent lap clocks in a synchronized initial-pit capture.

Requires D7FE/D86C probes. This covers initial setup and first laps, not native
mode-specific timer resets or the separate result-duration clock.
"""
import argparse
from pathlib import Path
import struct
from check_timing_retune import events


def u32(data, off):
    return struct.unpack_from('>I', data, off)[0]


def check(root):
    game = int((root / 'game-base.txt').read_text(), 0)
    base = int((root / 'dump-base.txt').read_text(), 0)
    chip = (root / 'chip.bin').read_bytes()
    data = (root / 'final-code.bin').read_bytes()
    frame = u32(chip, game+0xca46)-base
    assert 0 <= frame < len(data)
    lap = data.find(b'PDLAP001', frame, min(len(data), frame+16384))
    assert lap >= 0
    setup = (root / 'probe-0xe976-chip.bin').read_bytes()
    epoch = u32(setup, game+0xa6e+0x206)
    assert u32(data, lap+8) == epoch, 'Stable lap epoch differs from native initialization'
    counts = {0xd7fe: 0, 0xd86c: 0}
    last = None
    for event in events(root):
        if event['off'] not in counts:
            continue
        state = event['PDPOPP_EVENT']
        assert state[1] == 1
        expected = (epoch + state[5]-state[13]+18) & 0xffffffff
        assert state[20] == expected, 'Lap read includes a changing physical/native clock offset'
        counts[event['off']] += 1
        last = expected
    assert all(n >= 4 for n in counts.values()), 'Need all four opponents completing a lap'
    assert u32(data, lap+12) >= sum(counts.values())
    assert u32(data, lap+16) == last
    incoming, outgoing = struct.unpack_from('>HH', data, lap+20)
    expected_flags = (incoming & 16) | (8 if last & 0x80000000 else 0) | (4 if last == 0 else 0)
    assert outgoing & 31 == expected_flags, 'Lap clock does not reproduce MOVE.L flags'
    print(f'{root.name}: stable setup epoch; {counts[0xd7fe]} minimum-interval reads and '
          f'{counts[0xd86c]} lap-duration reads equal logical deadlines; guest flags pass')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    for root in parser.parse_args().captures:
        check(root)
