#!/usr/bin/env python3
"""Check initialized player lap/HUD clocks through an input-driven rescue.

Requires private/player clock probes at C7D2, E3BC/E3C4, CE28 and F118.
Also checks sampled opponent lap reads against a stable, unchanged lap epoch.
Checks native lap accounting if a real lap boundary occurs after rescue.
This does not certify complete trajectories or player victory.
"""
import argparse
import struct
from pathlib import Path


def check(root):
    # A terminal snapshot is required; a live prefix cannot pass this gate.
    after = (root/'final-code.bin').read_bytes()
    before = (root/'code.bin').read_bytes()
    chip = (root/'chip.bin').read_bytes()
    game = int((root/'game-base.txt').read_text(), 0)
    base = int((root/'dump-base.txt').read_text(), 0)
    frame = struct.unpack_from('>I', chip, game+0xca46)[0]-base
    lap = before.find(b'PDLAP001', frame, frame+16384)
    assert lap >= 0
    epoch, resets = [struct.unpack_from('>I', before, lap+i)[0] for i in (8, 24)]
    assert [struct.unpack_from('>I', after, lap+i)[0] for i in (8, 24)] == [epoch, resets], 'Lap epoch changed; this checker needs reset-boundary observations'
    rows = []
    current = None
    names = ('PDPLAP_EVENT', 'PDPLAYER_CLOCK', 'PDSESSION_EVENT', 'PDPIT_EVENT', 'PDPOPP_EVENT')
    for line in (root/'swaps-gdb.txt').read_text().splitlines():
        v = line.split()
        if not v:
            continue
        if v[0] == 'PDTIME_EVENT':
            current = dict(field=int(v[1]), off=int(v[2], 16))
            rows.append(current)
        elif v[0] in names:
            assert current is not None and (current['field'], current['off']) == (int(v[1]), int(v[2], 16))
            current[v[0]] = list(map(int, v[3:]))
    accepted = [r for r in rows if r['off'] == 0xc7d2]
    returned = [r for r in rows if r['off'] == 0xce28]
    assert len(accepted) == len(returned) == 1, 'Need one accepted rescue and normal pit return'
    first, last = accepted[0], returned[0]
    assert last['field'] > first['field']
    start = first['PDPLAP_EVENT']
    assert start[0] == 1 and start[7] == 0, 'Rescue must begin with a valid lap clock'
    assert first['PDPLAYER_CLOCK'][1] == start[2]
    modal = hud = resumed = lap_reads = completed_laps = 0
    current_start = start[:5]
    pending_lap = None
    original = (Path('tmp/extracted/pd').read_bytes())[32:]
    for off, length in ((0xf7a0, 6), (0xf96c, 8), (0xf9d8, 6)):
        assert chip[game+off:game+off+length] == original[off:off+length], 'Synthetic lap/finish predicate installed'
    for row in rows:
        off = row['off']
        private = row.get('PDPLAP_EVENT')
        if private and first['field'] <= row['field'] <= last['field']:
            assert private[:5] == start[:5] and private[6:8] == start[6:8], 'Rescue reset or advanced lap accounting'
            assert row['PDPLAYER_CLOCK'][1] == start[2], 'Rescue changed native lap start'
        if off in (0xe3bc, 0xe3c4) and row['PDPIT_EVENT'][0]:
            assert row['PDSESSION_EVENT'][8] == row['PDSESSION_EVENT'][13] == 0
            assert private is not None and private[0] == 1
            modal += 1
        if off == 0x10c00 and row['field'] > last['field']:
            clock = row['PDPLAYER_CLOCK']
            duration = private[1]-current_start[1]
            assert duration > 0 and private[4] == current_start[4]+1
            assert private[0] == 1 and private[3] == current_start[3] and private[7] == 0
            assert private[6] == clock[9] == duration, 'Lap subtraction differs from logical elapsed time'
            assert private[2] == clock[1] == clock[10], 'Native lap timestamp store changed'
            assert row['PDSESSION_EVENT'][13] == 1
            assert pending_lap is None, 'Prior lap commit not observed'
            pending_lap = (duration, clock[3]+duration, min(clock[4], duration), clock[5]+1)
            current_start = private[:5]
        if off == 0xf118 and row['PDSESSION_EVENT'][8] and private[0]:
            assert row['PDPLAYER_CLOCK'][6] & 0x8000 and row['PDPLAYER_CLOCK'][8] == 0, 'Expected ordinary human driving HUD'
            session = row['PDSESSION_EVENT']
            expected = max(0, session[14]-(0 if session[13] else 4)-private[1])
            assert row['PDPLAYER_CLOCK'][9] == private[8] == expected
            assert row['PDPLAYER_CLOCK'][1] == private[2] and private[7] == 0
            hud += 1
            if row['field'] > last['field']:
                assert private[:5] == current_start, 'Resumed HUD changed lap origin outside an observed boundary'
                if pending_lap is not None:
                    clock = row['PDPLAYER_CLOCK']
                    assert tuple(clock[2:6]) == pending_lap, 'Native lap/total/best/index accounting differs'
                    print(f'  Natural completed lap: {pending_lap[0]*5} ms; native total/best/lap index agree')
                    completed_laps += 1
                    pending_lap = None
                assert session[14] >= last['PDPIT_EVENT'][6], 'Resumed lap clock excluded the pit interval'
                resumed += 1
        if off in (0xd7fe, 0xd86c):
            opponent = row['PDPOPP_EVENT']
            assert opponent[1] == 1
            expected = (epoch+opponent[5]-opponent[13]+18) & 0xffffffff
            assert opponent[20] == expected, 'Opponent lap read used a different clock domain'
            lap_reads += 1
    assert last['PDPIT_EVENT'][:2] == [0, 1], 'Native pit did not return through interrupted tail'
    assert pending_lap is None, 'Unobserved native lap commit'
    assert modal >= 10 and hud >= 30 and resumed >= 10 and lap_reads >= 4, 'Insufficient modal/resumed/lap-read coverage'
    pit_ms = 5*(last['PDPIT_EVENT'][6]-last['PDPIT_EVENT'][5])
    print(f'{root.name}: initialized private/native lap starts preserved across {pit_ms} ms in the pit; {modal} inactive pit observations')
    print(f'  {hud} exact logical HUD readings, {resumed} resumed; {lap_reads} stable-domain opponent lap reads')
    print(f'  {completed_laps} natural completed player laps verified; full trajectories, victory and performance are not certified')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    check(parser.parse_args().capture)
