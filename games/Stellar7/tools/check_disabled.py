#!/usr/bin/env python3
"""Check disabled-game code against the original relocated executable.

Reports six audited native mutable data areas embedded in the code hunk
separately. Every other byte must match, including exact allowed menu-fixture
patches. No compiled simulation patch may overlap an excluded data area.
"""
import argparse
import json
import re
import struct
from pathlib import Path
from patchlist import decode, slave_code
from stellar7_report import GAME, locate


def hunks(path):
    blob = Path(path).read_bytes()
    cursor = 0

    def word():
        nonlocal cursor
        value = struct.unpack_from('>I', blob, cursor)[0]
        cursor += 4
        return value

    assert word() == 0x3f3, 'not an Amiga executable'
    assert word() == 0, 'named resident libraries unsupported'
    count, first, last = word(), word(), word()
    assert first == 0 and last + 1 == count == 2, 'expected two game hunks'
    sizes = [word() & 0x3fffffff for _ in range(count)]
    result = []
    for index in range(count):
        kind = word() & 0x3fffffff
        assert kind in (0x3e9, 0x3ea, 0x3eb), hex(kind)
        size = word()*4
        assert size <= sizes[index]*4
        data = bytearray(size) if kind == 0x3eb else bytearray(blob[cursor:cursor+size])
        assert len(data) == size, 'truncated hunk body'
        if kind != 0x3eb:
            cursor += size
        relocations = []
        while True:
            command = word()
            if command == 0x3f2:
                break
            assert command == 0x3ec, f'unsupported hunk command {command:#x}'
            while n := word():
                target = word()
                assert target < count
                for _ in range(n):
                    offset = word()
                    assert offset % 2 == 0 and offset + 4 <= size
                    relocations.append((offset, target))
        assert len({off for off, _ in relocations}) == len(relocations)
        data.extend(bytearray(sizes[index]*4-len(data)))
        result.append((data, relocations))
    assert cursor == len(blob), 'unexpected trailing executable data'
    return result


# These are data objects inside HUNK_CODE, not instruction patches. Native
# writers: $2514/$2548/$25e6 (runtime bases); $14e00/$14e0a (clip bounds);
# $1d934..$1d97a (20-byte edge records); $1d8a8/$1d5e8/$1d52c (blit state);
# $1e986/$1ea1a..$1ea26 (span state); $2019a/$20244 (decompression state).
NATIVE_DATA = (
    (0x28ce, 12, 'runtime bases'),
    (0x14c78, 4, 'clip bounds'),
    (0x1d318, 400, 'twenty edge records'),
    (0x1d4a8, 7, 'edge/blitter state'),
    (0x1e948, 10, 'span state'),
    (0x20004, 14, 'decompression word and twelve-byte input buffer'),
)


def native_data_guards(code, relocations):
    # Guard the native address formation as well as representative stores.
    for offset, expected in {
        0x24f8: '43fa03d4', 0x2514: '2288',
        0x2544: '41fa038c2080', 0x25e2: '41fa02f22080',
        0x14e00: '33f9', 0x14e0a: '33f9',
        0x1d89e: '207c', 0x1d934: '21400004',
        0x1d94e: '31400008', 0x1d97a: '317c00000012',
        0x1d980: 'd1fc00000014', 0x1d8a8: '33fc000f',
        0x1d5e8: '23c1', 0x1d52c: '13f00000',
        0x1e986: '23ef0040', 0x1ea1a: '33c5',
        0x1ea20: '33c7', 0x1ea26: '33c4',
        0x2019a: '33c2', 0x2023e: '4879', 0x20244: '4eb9',
    }.items():
        guard = bytes.fromhex(expected)
        assert code[offset:offset+len(guard)] == guard, f'native writer changed at {offset:#x}'
    for offset, target in {
        0x14e06: 0x14c78, 0x14e10: 0x14c7a,
        0x1d8a0: 0x1d318, 0x1d8ac: 0x1d4a8,
        0x1d5ea: 0x1d4aa, 0x1d530: 0x1d4ae,
        0x1e98a: 0x1e948, 0x1ea1c: 0x1e94c,
        0x1ea22: 0x1e94e, 0x1ea28: 0x1e950,
        0x2019c: 0x20004, 0x20240: 0x20006,
    }.items():
        assert (offset, 0) in relocations
        assert struct.unpack_from('>I', code, offset)[0] == target


def patch_size(command, argument):
    if command in ('P', 'PS'):
        return 6
    if command == 'PSS':
        return 6+int(argument.split('nops=')[1])
    if command == 'NOP':
        return int(argument, 16)
    assert command in ('B', 'W', 'L'), f'unsupported simulation patch {command}'
    return {'B': 1, 'W': 2, 'L': 4}[command]


def inspect(folder, listing, allow_menu_fixture=False):
    folder, listing = Path(folder), Path(listing)
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    symbols = {name: int(offset, 16) for name, offset in re.findall(
        r'^(\w+)\s+00:([0-9A-F]+)', listing.read_text(encoding='latin1'), re.M)}
    metadata = json.loads((folder/'metadata.json').read_text())
    assert not re.search(r'\bCUSTOM1=(?!0(?:\s|$))\S+', metadata['whd_args']), 'CUSTOM1 is enabled'
    meta = {key: int(value, 0) for key, value in re.findall(
        r'^(code|data|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    original = hunks(GAME)
    expected, relocations = original[0]
    assert len(expected) == 0x25360 and len(original[1][0]) == 0x823c
    native_data_guards(expected, relocations)
    excluded = {i for start, size, _ in NATIVE_DATA for i in range(start, start+size)}
    slave = slave_code(folder/'slave.slave')
    simulation_patches = []
    for name, start in symbols.items():
        if not (name.startswith('s60_') and name.endswith('_patches')):
            continue
        for offset, command, argument in decode(slave, start):
            if command == 'END':
                break
            size = patch_size(command, argument)
            assert 0 <= offset < offset+size <= len(expected), 'patch outside game code'
            assert not any(i in excluded for i in range(offset, offset+size)), f'{name} overlaps native data'
            simulation_patches.append((offset, size))
    assert simulation_patches, 'SIM60 patch lists absent'
    bases = (meta['code'], meta['data'])
    for offset, target in relocations:
        value = struct.unpack_from('>I', expected, offset)[0]
        struct.pack_into('>I', expected, offset, (value+bases[target]) & 0xffffffff)
    patches = []
    if allow_menu_fixture:
        assert re.search(r'\bCUSTOM5=1(?:\s|$)', metadata['whd_args'])
        assert not re.search(r'\bCUSTOM3=(?!0(?:\s|$))\S+', metadata['whd_args']), 'input fixture unsupported'
        loaded = locate(memory, slave, meta['base'], header=32)
        assert loaded is not None, 'loaded slave not found'
        start = symbols['fixture_patches']
        for offset, command, argument in decode(slave, start):
            if command == 'END':
                break
            assert command == 'PS', f'unsupported fixture patch {command}'
            assert offset in (0x4582, 0xb1f4, 0xb8c4), 'unexpected menu-fixture hook'
            target = int(argument.removeprefix('slave:'), 16)
            assert target in (symbols['fixture_begin'], symbols['fixture_escape'])
            expected[offset:offset+6] = b'\x4e\xb9'+struct.pack('>I', loaded+target)
            patches.append(offset)
        assert sorted(patches) == [0x4582, 0xb1f4, 0xb8c4]
    actual = memory[meta['code']-meta['base']:meta['code']-meta['base']+len(expected)]
    assert len(actual) == len(expected)
    differences = [i for i, (a, b) in enumerate(zip(expected, actual)) if a != b and i not in excluded]
    assert not differences, f'{len(differences)} unexpected code bytes at hunk offsets: '+', '.join(hex(i) for i in differences[:24])
    return dict(hunk_bytes=len(expected), checked_bytes=len(expected)-len(excluded),
                native_mutable_data=[dict(offset=hex(start), bytes=size, purpose=purpose)
                                     for start, size, purpose in NATIVE_DATA],
                relocated_longs=len(relocations), simulation_patch_ranges=len(simulation_patches),
                exact_menu_fixture_offsets=[hex(i) for i in patches], unexpected_bytes=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    parser.add_argument('--allow-menu-fixture', action='store_true')
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture, args.listing, args.allow_menu_fixture), indent=2))
