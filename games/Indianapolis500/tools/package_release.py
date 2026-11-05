#!/usr/bin/env python3
"""Package the installed release: the v3.0 SPS 0686 installed archive with the new slave and
ReadMe (make dist, through game.sh's game_dist).

    python3 tools/package_release.py --dist DIR [--force]

Reads tmp/archives/Indianapolis500_v3.0_0686.lha, tmp/build/release/Indianapolis500.Slave and
release/ReadMe; writes DIR/Indianapolis500_v<version>_0686.lha and its .sha256. Only the
members Indianapolis500/Indianapolis500.Slave and Indianapolis500/ReadMe change: they are
stored (-lh0-) with the version date from the slave's info string, and every other member's
header and packed bytes are copied unchanged, so the game data, icons, manual and hints are
the original archive's bytes.
"""
import argparse
import hashlib
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / 'tmp/archives/Indianapolis500_v3.0_0686.lha'
ORIGINAL_SHA256 = '4841b1dfa2a6dd22b47e23c9f438a67f10a353be44b33fec880af32387a8aba4'
SLAVE = ROOT / 'tmp/build/release/Indianapolis500.Slave'
README = ROOT / 'release/ReadMe'
LHA = os.environ.get('LHA', os.path.expanduser('~/.local/share/amiga/lha-compressor/src/lha'))
# Level-1 headers hold the file name; the drawer (Indianapolis500/) is in an extension.
SLAVE_MEMBER = b'Indianapolis500.Slave'
README_MEMBER = b'ReadMe'
DRAWER = 'Indianapolis500'
# Instrument magics (VERIFY, DRIVING_TEST, TIMING builds) that must not ship.
INSTRUMENTS = [b'I5PV', b'I5DR', b'I5TM']


def crc16(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xa001 if crc & 1 else crc >> 1
    return crc


def repack(blob, replacements, dos_date):
    """The archive with the named level-1 members replaced by stored copies."""
    out = bytearray()
    p = 0
    changed = []
    while blob[p]:
        hlen = blob[p] + 2
        head = bytearray(blob[p:p + hlen])
        assert head[20] == 1, 'level-1 headers only'
        assert sum(head[2:]) & 255 == head[1], 'header checksum'
        packed = struct.unpack_from('<I', head, 7)[0]
        n = head[21]
        name = bytes(head[22:22 + n])
        end = p + hlen + packed
        if name in replacements:
            crc_offset = None
            q = p + hlen
            extlen = struct.unpack_from('<H', head, hlen - 2)[0]
            while extlen:
                assert blob[q] in (0, 2, 0x40), f'unexpected extension {blob[q]:x}'
                if blob[q] == 0:
                    crc_offset = q - p + 1
                nextlen = struct.unpack_from('<H', blob, q + extlen - 2)[0]
                q += extlen
                extlen = nextlen
            extensions = blob[p + hlen:q]
            data = replacements[name]
            head[2:7] = b'-lh0-'
            struct.pack_into('<II', head, 7, len(extensions) + len(data), len(data))
            struct.pack_into('<I', head, 15, dos_date)
            struct.pack_into('<H', head, 22 + n, crc16(data))
            head[1] = sum(head[2:]) & 255
            full = bytearray(head + extensions)
            if crc_offset is not None:
                struct.pack_into('<H', full, crc_offset, 0)
                struct.pack_into('<H', full, crc_offset, crc16(full))
            out += full + data
            changed.append(name)
        else:
            out += blob[p:end]
        p = end
    assert blob[p:] == b'\x00' and set(changed) == set(replacements), changed
    out += b'\x00'
    return bytes(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--dist', required=True, type=Path)
    ap.add_argument('--force', action='store_true', help='replace an existing archive')
    args = ap.parse_args()

    blob = ORIGINAL.read_bytes()
    if hashlib.sha256(blob).hexdigest() != ORIGINAL_SHA256:
        sys.exit(f'{ORIGINAL.relative_to(ROOT)} is not the pinned original (make unpack)')
    slave = SLAVE.read_bytes()
    m = re.search(rb'Version (\d[^\s\x00]*) \((\d\d)\.(\d\d)\.(\d{4})\)', slave)
    if not m:
        sys.exit(f'{SLAVE.relative_to(ROOT)}: no "Version <v> (dd.mm.yyyy)" info string')
    version = m.group(1).decode()
    day, month, year = (int(x) for x in m.groups()[1:])
    for magic in INSTRUMENTS:
        if magic in slave:
            sys.exit(f'the release slave contains the instrument {magic.decode()}')
    readme = README.read_bytes()
    if f'version {version} '.encode() not in readme:
        sys.exit(f'release/ReadMe has no history entry for version {version}')

    out = repack(blob, {SLAVE_MEMBER: slave, README_MEMBER: readme},
                 ((year - 1980) << 25) | (month << 21) | (day << 16))
    args.dist.mkdir(parents=True, exist_ok=True)
    dest = args.dist / f'Indianapolis500_v{version}_0686.lha'
    if dest.exists() and not args.force:
        sys.exit(f'{dest} exists (FORCE=1 replaces it)')

    # The archive must test clean and extract to the new members.
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
        new = Path(tmp) / dest.name
        new.write_bytes(out)
        test = subprocess.run([LHA, 't', str(new)], capture_output=True, text=True)
        if test.returncode:
            sys.exit(f'lha t failed:\n{test.stdout}{test.stderr}')
        check = Path(tmp) / 'x'
        subprocess.run([LHA, f'xqw={check}', str(new)], check=True)
        assert (check / DRAWER / SLAVE_MEMBER.decode()).read_bytes() == slave
        assert (check / DRAWER / README_MEMBER.decode()).read_bytes() == readme

    dest.write_bytes(out)
    sha = hashlib.sha256(out).hexdigest()
    dest.with_name(dest.name + '.sha256').write_text(f'{sha}  {dest.name}\n')
    print(f'{dest}  (version {version}; {len(out)} bytes; SHA-256 {sha})')


if __name__ == '__main__':
    main()
