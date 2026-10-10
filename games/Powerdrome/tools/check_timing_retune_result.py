#!/usr/bin/env python3
"""Check a VERIFY-injected winner during initial/rescue pit retune catch-up.

This proves control flow and ownership at a forced branch outcome, not natural
lap detection or final ranking accuracy. It also requires cleanup and a fresh
driving session after the injected qualifying result.
"""
import argparse
import struct
from pathlib import Path
from check_timing_retune import events


def check(root, rescue=False):
    rows = events(root)
    candidates = [(i, e) for i, e in enumerate(rows)
                  if e['off'] == 0x14090]
    index, before = candidates[1 if rescue else 0]
    tail = rows[index:]
    native = next(e for e in tail if e['off'] == 0xe8d4)
    finish_index, finish = next((i, e) for i, e in enumerate(tail) if e['off'] == 0xbfb0)
    clean = next(e for e in tail[finish_index + 1:] if e['off'] == 0xbfb6)
    entry = [e for e in rows[:index] if e['off'] == 0x103a2][-1]
    b, n = before['PDPOPP_EVENT'], native['PDPOPP_EVENT']
    r, f, c = [e['PDRETUNE_EVENT'] for e in (native, finish, clean)]
    assert len(r) == len(f) == len(c) == 11
    assert r[0:2] == [0, 1] and r[5] == 1 and r[10] == 0
    assert n[1] == n[2] == n[6] == n[22] == 0
    assert n[8] == b[8], 'Interrupted update was counted as complete'
    assert n[7] - n[8] == r[8] > 0, 'Assigned work was not explicitly retired'
    assert (r[2] - b[4] + b[6]) == r[8] * 18 + r[9], 'Retired time is not conserved'
    assert n[17:19] == b[17:19], 'Counter/random ownership leaked from interrupted update'
    assert r[6] & 31 == r[7] & 31
    active = [e for e in tail[:finish_index] if e['PDRETUNE_EVENT'][0] and e['off'] == 0xd606]
    returned = [e for e in tail[:finish_index] if e['PDRETUNE_EVENT'][0] and e['off'] == 0xd7f0]
    assert len(active) == len(returned) == 1, 'Catch-up continued after the winner'
    assert returned[0]['PDRETUNE_EVENT'][1] == 1
    assert native['arrays'] == returned[0]['arrays'], 'Later opponents moved after the winning return'
    x, y = entry['PDMREG_EVENT'], finish['PDMREG_EVENT']
    assert y[0] & 65535 == r[3], 'Wrong winning opponent delivered'
    assert y[15] == x[15] + (8 if rescue else 4), 'Wrong native result stack depth'
    assert f[1] == f[5] == f[10] == 1
    assert c[0] == c[1] == 0 and c[10] == 1, 'Result gate failed to clear modal ownership'
    session = clean['PDSESSION_EVENT']
    assert session[13] == session[18] == session[19] == session[20] == 0
    assert session[16] == session[17] and session[21] == session[22]
    assert clean['PDINITIAL_EVENT'][0] == 0, 'Initial-pit identity survived result exit'
    closure = next(e for e in tail[finish_index + 1:] if e['off'] == 0xc2aa)
    setup = next(e for e in tail if e['field'] > closure['field'] and e['off'] == 0xe8d4)
    assert setup['PDRETUNE_EVENT'][0:2] == [0, 0]
    assert setup['PDPOPP_EVENT'][0:3] == [0, 0, 0], 'Opponent ownership survived session cleanup'
    assert setup['PDSESSION_EVENT'][8] == 0, 'Player clock survived session cleanup'
    fresh = next(e for e in tail if e['field'] > setup['field'] and e['off'] == 0xcedc)
    fs, ft = fresh['PDSESSION_EVENT'], fresh['PDPOPP_EVENT']
    assert fs[0] == setup['PDSESSION_EVENT'][0] + 1 and fs[1] == setup['PDSESSION_EVENT'][1]
    assert fs[8] == fs[18] == 1 and fs[11] == 0 and fs[12] == 1
    assert ft[0] == 1 and ft[1] == ft[2] == ft[6] == 0 and ft[7] == ft[8] == 1
    assert ft[13] == ft[25] > r[2], 'Fresh opponents inherited the retired timeline'
    game = int((root / 'game-base.txt').read_text(), 0)
    initial = (root / 'chip.bin').read_bytes()
    final = (root / 'final-chip.bin').read_bytes()
    mode = lambda data, off: struct.unpack_from('>H', data, game + 0xa6e + off)[0]
    assert mode(initial, 0xc0) == 65535, 'Fixture must begin in qualifying'
    assert all(mode(final, off) == 0 for off in (0xb6, 0xbe, 0xc0, 0xc4, 0xc8)), 'Fresh race mode not reached'
    print(f'{root.name}: one winner delivered with correct {"rescue" if rescue else "initial"} result stack; '
          f'{r[8]} assigned updates + {r[9] * 5} ms debt explicitly retired')
    print('  First partial update not counted complete; no later opponent motion; counter/RNG/guest flags restored')
    print('  Native cleanup and qualifying-to-race transition pass; fresh player/opponent clocks start without retired debt')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    p.add_argument('--rescue', action='store_true')
    a = p.parse_args()
    check(a.capture, a.rescue)
