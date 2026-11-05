#!/usr/bin/env python3
"""Check prepared non-interlaced scene Copper lists, not active DMA or scanout.

Scoped to the normal four-plane scene: both native buffers must have complete,
unambiguous colour/plane moves matching their bitmap and current colour map.
"""
import argparse
from pathlib import Path
import struct
from weather_palette_state import snapshot


def check(root, final=False):
    prefix = 'final-' if final else ''
    chip = (root / (prefix + 'chip.bin')).read_bytes()
    other = (root / (prefix + 'code.bin')).read_bytes()
    game = int((root / 'game-base.txt').read_text(), 0)
    base = int((root / 'dump-base.txt').read_text(), 0)
    palette = snapshot(root, final)

    def read(address, size):
        assert address > 0 and address % 2 == 0, 'Invalid display pointer'
        if address + size <= len(chip):
            return chip[address:address + size]
        assert base <= address and address + size <= base + len(other), 'Display data outside capture'
        return other[address - base:address - base + size]

    def pointer(address):
        return struct.unpack('>I', read(address, 4))[0]

    assert palette['view'] == 0, 'Only normal scene view supported'
    lists = []
    for long_slot, short_slot, bitmap in ((0x47d2, 0x47d6, 0x4696), (0x47da, 0x47de, 0x46be)):
        assert pointer(game + short_slot) == 0, 'Interlace needs separate validation'
        node = pointer(game + long_slot)
        nxt, start, capacity = struct.unpack('>IIh', read(node, 10))
        assert nxt == 0 and 0 < capacity <= 4096, 'Unexpected Copper chain or capacity'
        assert 0 < start < len(chip) and start + capacity * 4 <= len(chip), 'Copper instructions outside chip memory'
        moves = {}
        for index in range(capacity):
            register, value = struct.unpack('>HH', read(start + index * 4, 4))
            if (register, value) == (0xffff, 0xfffe):
                break
            if register & 1:
                continue
            assert register <= 0x1fe, 'Invalid Copper register'
            if 0x180 <= register <= 0x19e or 0xe0 <= register <= 0xee:
                assert register not in moves, 'Multiple colour/plane writes require raster-aware validation'
                moves[register] = value
        else:
            raise AssertionError('Missing Copper terminator')
        assert tuple(moves[0x180 + 2 * i] for i in range(16)) == palette['current'], 'Prepared Copper palette differs from current colour map'
        header = read(game + bitmap, 8)
        assert header[5] == 4, 'Expected four-plane scene bitmap'
        for plane in range(4):
            address = (moves[0xe0 + plane * 4] << 16) | moves[0xe2 + plane * 4]
            assert address == pointer(game + bitmap + 8 + 4 * plane), 'Copper selects wrong scene plane'
            assert 0 < address < len(chip), 'Displayed plane outside chip memory'
        lists.append(node)
    assert pointer(game + 0x4782) in lists and pointer(game + 0x4786) == 0, 'View selects neither prepared scene list'
    print(f'{root.name} {prefix or "initial"}: both prepared scene lists match all 16 colours and four bitmap planes; selected View belongs to the pair')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('captures', type=Path, nargs='+')
    args = p.parse_args()
    for root in args.captures:
        for final in (False, True):
            check(root, final)
    print('Prepared display structures only; active Copper selection, intermediate phases and scanout remain unverified.')
