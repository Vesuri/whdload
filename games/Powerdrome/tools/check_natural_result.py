#!/usr/bin/env python3
"""Validate a natural human race result and measure its clock-domain error.

Requires ordered read-only C094, C09E and C0A6 snapshots, then an anchor after
C0A6. The input route must reach an ordinary race without result injection.
--require-logical-time adds the eventual exact logical-result-clock gate.
"""
import argparse
from pathlib import Path
import re
import struct
from check_pilot_list import inspect


def u32(data, offset):
    return struct.unpack_from('>I', data, offset)[0]


def u16(data, offset):
    return struct.unpack_from('>H', data, offset)[0]


def check(root, require_logical_time=False):
    game = int((root / 'game-base.txt').read_text(), 0)
    base = int((root / 'dump-base.txt').read_text(), 0)
    state = game + 0xa6e
    before = (root / 'probe-0xc094-chip.bin').read_bytes()
    compute = (root / 'probe-0xc09e-chip.bin').read_bytes()
    ranked = (root / 'probe-0xc0a6-chip.bin').read_bytes()
    other = (root / 'probe-0xc094-other.bin').read_bytes()
    assert all(u16(before, state + x) == 0 for x in (0xb6, 0xbe, 0xc0, 0xc4, 0xc8))
    assert u16(before, game + 0xca44) == 0x4ef9
    frame = u32(before, game + 0xca46) - base
    assert 0 <= frame < len(other)
    def live_tag(tag):
        location = other.find(tag, frame, min(len(other), frame + 16384))
        assert location >= 0, f'Missing live {tag!r}'
        return location
    opp = live_tag(b'PDPOPP01')
    retune = live_tag(b'PDRETUNE')
    assert u32(other, retune + 24) == 0, 'Injected/deferred result is not a natural ordinary result'
    assert u16(other, opp + 8) == 1 and u16(other, opp + 10) == 0
    assert u16(other, opp + 12) > 0, 'Expected a winning opponent update interrupted by native results'
    start = u32(before, state + 0x22e)
    logical = u32(other, opp + 36)
    assert u32(compute, state + 0x22e) == start
    duration = u32(ranked, state + 0x22e)
    registers = (root / 'probe-0xc09e-registers.txt').read_text()
    value = re.search(r'^d7\s+0x([0-9a-f]+)', registers, re.M)
    assert value and int(value[1], 16) == duration, 'Result duration differs from the native committed value'
    result = inspect(ranked, game, require_sorted=True)
    assert not result['qualifying']
    target = u16(ranked, state + 0x266)
    assert target > 0 and result['nodes'][0]['lap'] == target
    assert result['nodes'][0]['id'] != 0, 'This fixture expects a natural opponent finish'
    assert sum(n['lap'] == target for n in result['nodes']) == 1
    expected = (logical - start) & 0xffffffff
    error = (duration - expected) & 0xffffffff
    if error & 0x80000000:
        error -= 1 << 32
    print(f'{root.name}: natural opponent {result["nodes"][0]["id"]} wins at lap {target}; '
          'all five native pilot links and sorted comparisons pass')
    print(f'  Reported duration {duration * 5} ms; logical winning duration {expected * 5} ms; '
          f'error {error * 5:+d} ms')
    if require_logical_time:
        assert error == 0, 'Result duration is not tied to the logical winning instant'
        result_state = live_tag(b'PDRSLT01')
        output = (root / 'probe-0xc0a6-other.bin').read_bytes()
        assert u16(output, result_state + 8) == u16(output, result_state + 10) == 1
        assert u32(output, result_state + 12) == u32(output, result_state + 32) == logical
        assert u32(output, result_state + 20) > 0
        input_ccr = u16(output, result_state + 28)
        expected_ccr = (input_ccr & 16) | (8 if logical & 0x80000000 else 0) | (4 if logical == 0 else 0)
        assert u16(output, result_state + 30) & 31 == expected_ccr, 'Guest clock-read flags differ from native MOVE.L'
        def registers_at(point):
            text = (root / f'probe-{point}-registers.txt').read_text()
            return {name: int(value, 16) for name, value in re.findall(r'^(d[0-7]|a[0-6]|sp)\s+0x([0-9a-f]+)', text, re.M)}
        first, last = registers_at('0xc094'), registers_at('0xc09e')
        preserved = [f'd{i}' for i in range(7)] + [f'a{i}' for i in range(7)] + ['sp']
        assert all(first[name] == last[name] for name in preserved), 'Duration-clock wrapper changed a native caller register or stack'
        final = (root / 'final-code.bin').read_bytes()
        assert u16(final, result_state + 8) == u16(final, result_state + 10) == 0, 'Winning clock leaked past session cleanup'
        physical_gap = u32(output, result_state + 24) - logical
        print(f'  Latched opponent time, preserved registers/stack and guest MOVE.L flags verified; native read was {physical_gap * 5:+d} ms later')
        print('  Winning-clock ownership cleared by native session cleanup')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures', type=Path, nargs='+')
    p.add_argument('--require-logical-time', action='store_true')
    a = p.parse_args()
    for capture in a.captures:
        check(capture, a.require_logical_time)
