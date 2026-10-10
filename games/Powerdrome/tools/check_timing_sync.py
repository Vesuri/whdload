#!/usr/bin/env python3
"""Validate actual test-only pit synchronization events, without claiming equivalence."""
import argparse
import json
from pathlib import Path
import struct


def u32(data, off):
    return struct.unpack_from('>I', data, off)[0]


def check(root):
    cfg = json.loads((root / 'configuration.json').read_text())
    assert cfg['TIMING_EARLY'] == '1' and cfg['OPPONENT_STATE'] == '1'
    assert int(cfg['ANCHOR'], 0) == 0xbc3a
    game = int((root / 'game-base.txt').read_text(), 0)
    base = int((root / 'dump-base.txt').read_text(), 0)
    chip = (root / 'chip.bin').read_bytes()
    data = (root / 'final-code.bin').read_bytes()
    assert struct.unpack_from('>H', chip, game+0xca44)[0] == 0x4ef9
    frame = u32(chip, game+0xca46)-base
    assert 0 <= frame < len(data), 'Invalid live timing-code pointer'
    def tag(name):
        pos = data.find(name, frame, min(frame+16384, len(data)))
        assert pos >= 0, f'Missing live diagnostic {name!r}'
        return pos
    sync, pit, retune, opponent = map(tag, (b'PDSYNC01', b'PDPIT001', b'PDRETUNE', b'PDPOPP01'))
    arrival, release, return_arrival, return_release, retunes, returns = struct.unpack_from('>6I', data, sync+8)
    assert (retunes, returns) == (1, 1), 'Need exactly one synchronized initial pit'
    assert arrival <= release == 3600, 'Retune missed its 18-second boundary'
    assert return_arrival <= return_release == 4800, 'Return missed its 24-second boundary'
    origin = u32(data, opponent+52)-18
    assert u32(data, retune+12)-origin == release, 'Actual retune cutoff differs from fixture release'
    assert u32(data, pit+28)-origin == return_release, 'Actual pit exit differs from fixture release'
    print(f'{root.name}: retune arrived {arrival*5} ms, released {release*5} ms; '
          f'pit return arrived {return_arrival*5} ms, released {return_release*5} ms')
    print('  Native retune cutoff and pit exit match both requested logical event times')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path, nargs='+')
    for root in parser.parse_args().captures:
        check(root)
