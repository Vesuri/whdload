#!/usr/bin/env python3
"""Read native weather palette state; stored colours do not prove displayed pixels."""
import argparse
import json
from pathlib import Path
import struct


def interpolate(source, target, phase):
    """Reproduce the signed MULS/DIVS/ASR component arithmetic at hunk $17306."""
    assert 0 <= source <= 0xfff and 0 <= target <= 0xfff
    assert 0 <= phase <= 15
    result = 0
    for shift in (0, 4, 8):
        start = (source >> shift) & 15
        end = (target >> shift) & 15
        product = ((end - start) << 8) * phase
        quotient = abs(product) // 15
        if product < 0:
            quotient = -quotient
        component = start + (quotient >> 8)
        assert 0 <= component <= 15
        result |= component << shift
    return result


def snapshot(root, final=False):
    prefix = 'final-' if final else ''
    chip = (root / (prefix + 'chip.bin')).read_bytes()
    other = (root / (prefix + 'code.bin')).read_bytes()
    game = int((root / 'game-base.txt').read_text(), 0)
    base = int((root / 'dump-base.txt').read_text(), 0)

    def read(address, size):
        assert address >= 0 and address % 2 == 0, 'Invalid palette address'
        if address + size <= len(chip):
            return chip[address:address + size]
        assert base <= address and address + size <= base + len(other), 'Palette outside captured memory'
        return other[address - base:address - base + size]

    def word(address):
        return struct.unpack('>H', read(address, 2))[0]

    def pointer(address):
        value = struct.unpack('>I', read(address, 4))[0]
        assert value != 0, 'Missing palette pointer'
        return value

    state = game + 0xa6e
    saved = pointer(state + 0x4b0)
    colormap = pointer(game + 0x4790)
    current = pointer(colormap + 4)
    track = word(state + 0x118)
    view = word(state + 0xaa)
    # Target words occupy $203e up to the following gear table at $204c.
    assert 0 <= track < (0x204c - 0x203e) // 2, 'Target colour index outside table'
    target = word(game + 0x203e + (0 if view else 2 * track))
    out = dict(track=track, view=view, transition=word(state + 0x4c6),
               transient=word(state + 0x4d0), source=word(state + 0x4b6), target=target,
               saved_pointer=saved, colormap_pointer=colormap, current_pointer=current,
               saved=struct.unpack('>16H', read(saved, 32)),
               current=struct.unpack('>16H', read(current, 32)))
    assert all(0 <= value <= 0xfff for value in (*out['saved'], *out['current'], out['source'], target)), 'Non-RGB4 palette value'
    return out


def check_restored(state):
    assert state['transition'] == state['transient'] == 0, 'Palette transition/effect remains active'
    assert state['saved'][5] == state['current'][5] == state['source'], 'Weather colour not restored'
    assert state['saved'] == state['current'], 'Saved palette differs from current colour table'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    parser.add_argument('--require-restored', action='store_true', help='Check both stored endpoints, not scanout or intermediate fades')
    args = parser.parse_args()
    for root in args.captures:
        for final in (False, True):
            state = snapshot(root, final)
            if args.require_restored:
                check_restored(state)
            print(json.dumps(dict(capture=root.name, phase='final' if final else 'initial',
                                  track=state['track'], view=state['view'], transition=state['transition'],
                                  transient=state['transient'], palettes_equal=state['saved'] == state['current'],
                                  weather_colour_restored=state['saved'][5] == state['current'][5] == state['source'])))
    print('Stored palette endpoints only; intermediate writes, publication and scanout remain separate.')


if __name__ == '__main__':
    main()
