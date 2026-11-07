#!/usr/bin/env python3
"""Check the release slave's two simulations against the development slaves.

The release Stellar7.Slave carries both simulations, each assembled alone from
src/payload.s (game.sh). Each must be byte-identical to the simulation code of its
development slave (Stellar7-Sim68000, Stellar7-Sim60, same build), except the
displacement words of its (_resload,pc) loads, which reach the copy's own _resload
instead of the loader's. Each copy must also sit at the same address modulo 4.

    tools/release_payloads.py [BUILD_DIR]   (default tmp/build/release)

BUILD_DIR holds Stellar7.Slave/.lst, Stellar7.<name>.bin/.lst and the development
VARIANT.Slave/.lst. Prints the result as JSON.
"""
import json
import re
import struct
import sys
from pathlib import Path
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev.patchlist import slave_code

ROOT = Path(__file__).resolve().parents[1]
PAYLOADS = {'Sim68000': 'Stellar7-Sim68000', 'Sim60': 'Stellar7-Sim60'}


def symbols(listing):
    return {name: int(offset, 16) for name, offset in re.findall(
        r'^(\w+)\s+00:([0-9A-F]+)', Path(listing).read_text(encoding='latin1'), re.M)}


def resload_sites(code, start, end, target):
    """Displacement words of MOVEA.L (d16,PC),An in code[start:end] that reach target."""
    sites = set()
    for word in range(start+2, end-1, 2):
        opcode = struct.unpack_from('>H', code, word-2)[0]
        if opcode & 0xf1ff == 0x207a and word+struct.unpack_from('>h', code, word)[0] == target:
            sites.add(word)
    return sites


def check(folder):
    folder = Path(folder)
    release = slave_code(folder/'Stellar7.Slave')
    merged = symbols(folder/'Stellar7.lst')
    result = {}
    for name, variant in PAYLOADS.items():
        payload = (folder/f'Stellar7.{name}.bin').read_bytes()
        own = symbols(folder/f'Stellar7.{name}.lst')
        assert own['timing_install'] == 0 and own['_resload'] == len(payload)-4, name
        assert payload[-4:] == bytes(4), name
        start, end = merged['s7_'+name.lower()], merged['s7_'+name.lower()+'_end']
        assert release[start:end] == payload, f'{name}: release slave does not carry the payload'
        direct = slave_code(folder/f'{variant}.Slave')
        theirs = symbols(folder/f'{variant}.lst')
        base, length = theirs['timing_install'], own['payload_end']
        assert start % 4 == base % 4, f'{name}: alignment differs from {variant}'
        reference = direct[base:base+length]
        assert len(reference) == length, f'{name}: {variant} is shorter than the payload'
        differences = {i for i in range(length) if payload[i] != reference[i]}
        ours = resload_sites(payload, 0, length, own['_resload'])
        theirs_sites = resload_sites(direct, base, base+length, theirs['_resload'])
        assert {site-base for site in theirs_sites} == ours, f'{name}: _resload loads differ'
        unexplained = sorted(i for i in differences if i & ~1 not in ours)
        assert not unexplained, f'{name}: {len(unexplained)} bytes differ from {variant}: ' + \
            ', '.join(hex(i) for i in unexplained[:16])
        result[name] = dict(development_variant=variant, bytes=length, release_offset=hex(start),
                            development_offset=hex(base), resload_loads=len(ours),
                            differing_bytes=len(differences),
                            other_bytes_identical=length-len(differences))
    return result


if __name__ == '__main__':
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'tmp/build/release'
    print(json.dumps(check(folder), indent=2))
