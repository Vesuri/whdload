#!/usr/bin/env python3
"""Check an explicitly forced native player-result branch; never natural victory.

Ordered F9EC/BFB0/C094/C09E/C0A6 snapshots and post-result cleanup are required.
The test intentionally does not require a winning player rank or completed race.
"""
import argparse
from pathlib import Path
import re
import struct
from check_pilot_list import inspect


def u32(data, off):
    return struct.unpack_from('>I', data, off)[0]


def u16(data, off):
    return struct.unpack_from('>H', data, off)[0]


def registers(root, off):
    text = (root/f'probe-{off}-registers.txt').read_text()
    values = {name: int(value, 16) for name, value in re.findall(r'^(d[0-7]|a[0-6]|sp)\s+0x([0-9a-f]+)', text, re.M)}
    assert len(values) == 16, 'Incomplete register snapshot'
    return values


def check(root):
    game = int((root/'game-base.txt').read_text(), 0)
    base = int((root/'dump-base.txt').read_text(), 0)
    before = (root/'probe-0xc094-chip.bin').read_bytes()
    data = (root/'probe-0xc094-other.bin').read_bytes()
    after = (root/'probe-0xc0a6-other.bin').read_bytes()
    ranked = (root/'probe-0xc0a6-chip.bin').read_bytes()
    final = (root/'final-code.bin').read_bytes()
    frame = u32(before, game+0xca46)-base
    assert 0 <= frame < len(data)
    def tag(value):
        pos = data.find(value, frame, frame+16384)
        assert pos >= 0
        return pos
    result, lap, opp = tag(b'PDRSLT01'), tag(b'PDLAP001'), tag(b'PDPOPP01')
    assert u32(data, result+52) == u32(data, result+56) == u32(data, result+60) == 1, 'Need one forced boundary, checkpoint admission and finish decision'
    assert u32(data, result+44) == 1
    assert (u16(data, result+8), u16(data, result+10), u16(data, result+36)) == (1, 3, 0)
    state = game+0xa6e
    assert all(u16(before, state+x) == 0 for x in (0xb6, 0xbe, 0xc0, 0xc4, 0xc8))
    assert u32(data, lap+24) == 1
    start = u32(before, state+0x22e)
    assert start == u32(data, lap+32)
    winning = (u32(data, lap+8)+u32(data, result+48)-u32(data, opp+52)+18) & 0xffffffff
    assert u32(data, result+12) == u32(data, result+40) == winning
    assert u32(after, result+32) == winning
    duration = (winning-start) & 0xffffffff
    player = tag(b'PDPLAP01')
    assert u32(data, player+20) == 1 and u32(data, player+24) == 1
    assert u32(data, player+36) == 0, 'Synthetic lap unexpectedly used native reset fallback'
    assert u32(data, player+12) == u32(data, result+48)
    assert u32(data, player+16) == u32(before, state+0x206)
    assert u32(data, player+32) == duration
    assert u32(before, state+0x202) == u32(before, state+0x1b2) == duration, 'Native lap storage and accumulated total differ from logical duration'
    assert u32(ranked, state+0x22e) == duration
    assert registers(root, '0xc09e')['d7'] == duration
    initial, entry = registers(root, '0xf9ec'), registers(root, '0xbfb0')
    assert entry['d0'] == (initial['d0'] & 0xffff0000) | 0xffff
    assert all(initial[key] == entry[key] for key in initial if key != 'd0'), 'Player-entry wrapper changed native registers or unwound stack depth'
    first, last = registers(root, '0xc094'), registers(root, '0xc09e')
    assert all(first[key] == last[key] for key in first if key != 'd7'), 'Duration read changed caller registers or stack'
    incoming = u16(after, result+28)
    flags = (incoming & 16) | (8 if winning & 0x80000000 else 0) | (4 if winning == 0 else 0)
    assert u16(after, result+30) & 31 == flags
    assert all(u16(final, result+off) == 0 for off in (8, 10, 36)), 'Player result ownership leaked after cleanup'
    inspect(ranked, game, require_sorted=True)
    print(f'{root.name}: forced player-result branch reports {duration*5} ms, exactly its logical winning-step duration')
    print('  Source 3 consumed once; native sentinel, registers, stack, duration-read flags, five-pilot sorting and cleanup pass')
    print('  Synthetic lap duration and native accumulated total match the same logical interval')
    print('  This does not establish natural player victory, winning rank or a naturally completed lap')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture', type=Path)
    check(p.parse_args().capture)
