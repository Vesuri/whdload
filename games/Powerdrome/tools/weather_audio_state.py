"""Read native weather-audio resources; availability is not proof of playback.

The legacy PDWEFX cleanup fields describe this sound request, not bitmap cleanup.
Read only: never force the allocation guard or dereference a missing sample table.
"""
import argparse
import json
from pathlib import Path
import struct


def snapshot(chip, game):
    def word(offset):
        return struct.unpack_from('>H', chip, game + offset)[0]

    def long(offset):
        return struct.unpack_from('>I', chip, game + offset)[0]

    out = dict(available=long(0x4f74), allocation_size=long(0x53c),
               allocation_base=long(0x540), allocation_used=long(0x538),
               sample_table=long(0x5ae), suppressed=word(0xa6e + 0x2f4),
               channel3_status=word(0x48c4 + 6),
               channel3_period=word(0x48dc + 6))
    assert out['available'] in (0, 0xffffffff), 'Unexpected native resource guard'
    if not out['available']:
        return out
    lo = out['allocation_base']
    hi = lo + out['allocation_size']
    assert lo > 0 and hi <= len(chip), 'Native allocation outside captured chip memory'
    assert out['allocation_size'] == 404000, 'Availability without larger allocation'
    assert 0 < out['allocation_used'] <= out['allocation_size']
    table = out['sample_table']
    assert table % 2 == 0 and lo <= table and table + 360 <= hi, 'Invalid sample table'
    pointer, length, period = struct.unpack_from('>3I', chip, table + 48)
    # Native helper writes only the low word to AUDxLEN and AUDxPER.
    assert 0 < length <= 65535 and 0 < period <= 65535, 'Unexpected audio descriptor'
    assert pointer % 2 == 0 and lo <= pointer and pointer + 2 * length <= hi, 'Sample outside allocation'
    out.update(sample_pointer=pointer, sample_words=length, sample_period=period,
               volume=63, channel=3)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', nargs='+', type=Path)
    parser.add_argument('--require-available', action='store_true')
    args = parser.parse_args()
    for root in args.captures:
        game = int((root / 'game-base.txt').read_text(), 0)
        for prefix in ('', 'final-'):
            state = snapshot((root / (prefix + 'chip.bin')).read_bytes(), game)
            if args.require_available:
                assert state['available'], f'{root.name}/{prefix or "initial"}: optional samples absent'
            print(json.dumps(dict(capture=root.name, phase=prefix.rstrip('-') or 'initial', **state), sort_keys=True))


if __name__ == '__main__':
    main()
