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


# Native helper boundaries. Sample both to pair calls by stack and return address;
# other audio callers use this helper too, so arguments alone do not identify weather.
PROBES = (0x17836, 0x178e6, 0xc5fc, 0xc600)
REGISTERS = ('d0', 'd1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7',
             'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'sp')
EVENT_FIELDS = ('clock', 'available', 'suppressed', 'channel3_status',
                'channel3_period', 'return_address', *REGISTERS)


def probe_command(game, offset):
    assert offset in PROBES
    values = [f'*(unsigned int*){game + 0xf96:#x}',
              f'*(unsigned int*){game + 0x4f74:#x}',
              f'*(unsigned short*){game + 0xa6e + 0x2f4:#x}',
              f'*(unsigned short*){game + 0x48c4 + 6:#x}',
              f'*(unsigned short*){game + 0x48dc + 6:#x}',
              '*(unsigned int*)$sp']
    values += [f'(unsigned int)${reg}' for reg in REGISTERS]
    return ('printf "PDWAUDIO_EVENT %d ' + hex(offset) + ' ' +
            ' '.join(['%u'] * len(values)) + '\\n", $pd_field, ' +
            ', '.join(values) + '\n')


def parse_values(text):
    values = list(map(int, text.split()))
    assert len(values) == len(EVENT_FIELDS), 'Incomplete audio probe row'
    return dict(zip(EVENT_FIELDS, values))


def owned_return(chip, code, game, base):
    """Locate the actual installed wrapper's BSR return, not a stale slave copy."""
    assert chip[game + 0xbc8a:game + 0xbc8c] == bytes.fromhex('4ef9')
    assert chip[game + 0x112e6:game + 0x112e8] == bytes.fromhex('4ef9')
    start = struct.unpack_from('>I', chip, game + 0xbc8c)[0] - base
    end = struct.unpack_from('>I', chip, game + 0x112e8)[0] - base
    assert 0 <= start < end <= len(code) and end - start < 512
    assert code[start:start + 4] == bytes.fromhex('48e7fffe')
    matches = []
    for pos in range(start, end, 2):
        if code[pos] != 0x61:
            continue
        short = struct.unpack_from('>b', code, pos + 1)[0]
        displacement = short or struct.unpack_from('>h', code, pos + 2)[0]
        target = pos + 2 + displacement
        ret = pos + (2 if short else 4)
        if not 0 <= target <= len(code) - 6:
            continue
        if (code[target:target + 6] == b'\x4e\xf9' + struct.pack('>I', game + 0x17836)
                and code[ret:ret + 4] == bytes.fromhex('4cdf7fff')):
            matches.append(base + ret)
    assert len(matches) == 1, 'Missing or ambiguous installed weather-audio caller'
    return matches[0]


if __name__ == '__main__':
    main()
