#!/usr/bin/env python3
"""Read opening-wave shortcut setup results from an exact build snapshot."""
import argparse
import json
import re
import struct
from pathlib import Path
from stellar7_report import locate


def read(folder, listing):
    folder, listing = Path(folder), Path(listing)
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    symbols = listing.read_text(encoding='latin1')
    offset = int(re.search(r'^s60_encounter_results\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    size = struct.unpack_from('>I', binary, 28)[0]*4
    base = locate(memory, binary[32:32+size], meta['base'], header=32)
    assert base is not None
    at = base-meta['base']+offset
    signature = memory[at:at+4]
    assert signature in (b'BE60', b'BE61', b'BE62', b'BE63', b'BE64')
    result = dict(zip(('setups', 'errors', 'session', 'level', 'original_progress', 'target'),
                    struct.unpack_from('>2HI3H', memory, at+4)))
    if signature in (b'BE61', b'BE62', b'BE63', b'BE64'):
        result['initial_enemies_cleared'] = struct.unpack_from('>H', memory, at+18)[0]
    if signature in (b'BE62', b'BE63', b'BE64'):
        result['requested_level'] = struct.unpack_from('>H', memory, at+20)[0]
    if signature == b'BE63':
        result.update(zip(('finish_setups', 'original_health', 'assigned_health', 'finish_tick'),
                          struct.unpack_from('>3HI', memory, at+22)))
    if signature == b'BE64':
        result.update(zip(('terrain_setups', 'prior_state', 'assigned_state', 'reserved', 'terrain_tick'),
                          struct.unpack_from('>4HI', memory, at+22)))
    return result


def validate(result):
    assert result['setups'] == 1 and result['errors'] == 0, result
    requested = result.get('requested_level', 0)
    assert result['level'] == requested and result['session'] == requested+1, result
    assert 0 <= result['original_progress'] <= result['target'], result
    assert 0 <= result['level'] <= 6 and 0 < result['target'] <= 255, result



def validate_finish(result):
    validate(result)
    assert result['requested_level'] == 6 and result['finish_setups'] == 1, result
    assert 1 <= result['original_health'] <= 127 and result['assigned_health'] == 1, result
    assert result['finish_tick'] > 0, result


def validate_terrain(result):
    validate(result)
    assert result['requested_level'] == 5 and result['terrain_setups'] == 1, result
    assert 0 <= result['prior_state'] <= 255 and result['assigned_state'] == 1, result
    assert result['reserved'] == 0 and result['terrain_tick'] > 0, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    parser.add_argument('--finished', action='store_true', help='require the explicit final-boss health setup')
    parser.add_argument('--terrain', action='store_true', help='require the explicit level-5 terrain state setup')
    args = parser.parse_args()
    result = read(args.capture, args.listing)
    print(json.dumps(result, indent=2))
    validate(result)
    if args.finished:
        validate_finish(result)

    if args.terrain:
        validate_terrain(result)
