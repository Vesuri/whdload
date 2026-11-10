#!/usr/bin/env python3
"""G4: rebuild Codetapper's installer archive with the new slave -> dist/ (LH5, level-1 headers).

    make dist        (game.sh game_dist: --dist names the output directory, --force
                      replaces an existing archive)

Input, kept local and verified against inputs.sha256: tmp/archives/FormulaOneGrandPrix.lha.
Output: <dist>/FormulaOneGrandPrixEnhanced-<version>-<YYYYMMDD>.lha (the repository's ignored
dist/; version and date from the slave's $VER, common/tools/package_release.py), with exactly
the input's members, and its .sha256 beside it.
Changed members are the current release build, tmp/build/release/F1GP.Slave, which make dist
has just built and whose build.json must match it and the source (G1: the enhancements on with
"Enhanced frame rate", which the icons set), release/ReadMe and the nine game launch icons, which get a
CUSTOM2=1 and a MEMCONFIG tooltype; everything else is copied byte for byte. The archive is re-extracted and
checked member by member against its stage and the original. LHA names LHa for UNIX
(Lhasa, the usual `lha`, cannot create archives).
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import re
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
# The shared packager's $VER rules (this file shares its module name, so load it by path).
_spec = importlib.util.spec_from_file_location(
    'common_package_release', ROOT.parents[1] / 'common/tools/package_release.py')
_common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_common)
version_of, date_of = _common.version_of, _common.date_of
LHA = os.environ.get('LHA', os.path.expanduser('~/.local/share/amiga/lha-compressor/src/lha'))
SOURCE = ROOT / 'tmp/archives/FormulaOneGrandPrix.lha'
TOP, SLAVE = 'FormulaOneGrandPrixHD', 'FormulaOneGrandPrix.slave'
ICONS = ('inf', 'romicon', 'newicon', 'newintro', 'newexot', 'newexot2', 'colicon', 'colintro',
         'colbox')
BUILD = ROOT / 'tmp/build/release'
# G1: the icons turn the release's enhancements on ("Enhanced frame rate", CUSTOM2 bit 0);
# E's fast areas need the alternative memory configuration.
TOOLTYPES = (b'CUSTOM2=1', b'MEMCONFIG=1')


def members(archive):
    return subprocess.run(['lsar', archive], capture_output=True, text=True,
                          check=True).stdout.splitlines()[1:]


def extract(archive, into):
    subprocess.run(['lha', f'xqw={into}', str(archive)], check=True)


def enhanced_icon(original):
    """Insert TOOLTYPES after the icon's PRELOAD tooltype.

    Locate the length-prefixed WHDLoad default tool, then validate the whole tooltype
    array. ROMIcon's leading colour line and the NewIcon image lines after the entries
    keep their places; image data, padding and trailing ColorIcon chunks are preserved.
    The stored array size includes the terminating null pointer.
    """
    marker = b'\x00\x00\x00\x08WHDLoad\x00'
    assert original[:2] == b'\xe3\x10' and original.count(marker) == 1
    start = original.index(marker) + len(marker)
    size = struct.unpack_from('>I', original, start)[0]
    assert size >= 4 and size % 4 == 0
    cursor, entries, after = start + 4, [], None
    for _ in range(size // 4 - 1):
        length = struct.unpack_from('>I', original, cursor)[0]
        value = original[cursor + 4:cursor + 4 + length]
        assert length and len(value) == length and value.endswith(b'\0')
        entries.append(value.rstrip(b'\0').upper())
        cursor += 4 + length
        if entries[-1] == b'PRELOAD':
            after = cursor
    assert entries.count(b'SLAVE=' + SLAVE.upper().encode()) == 1 and after
    assert not any(v.lstrip(b'(').startswith((b'CUSTOM2=', b'MEMCONFIG=')) for v in entries)
    addition = b''.join(struct.pack('>I', len(t) + 1) + t + b'\0' for t in TOOLTYPES)
    updated = (original[:start] + struct.pack('>I', size + 4 * len(TOOLTYPES))
               + original[start + 4:after] + addition + original[after:])
    # Reversing the insertion must reproduce every original byte, including artwork.
    assert (updated[:start] + struct.pack('>I', size) + updated[start + 4:after]
            + updated[after + len(addition):]) == original
    return updated


def archive(stage, names, out, changed):
    out.unlink(missing_ok=True)
    subprocess.run([LHA, 'a1o5q2', str(out), *names], cwd=stage, check=True)
    test = subprocess.run([LHA, 't', str(out)], capture_output=True, text=True)
    assert test.returncode == 0, test.stdout + test.stderr
    assert sorted(members(out)) == sorted(names), out  # LHa for UNIX sorts the members
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as new, \
            tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as old:
        extract(out, new)
        extract(SOURCE, old)
        for name in names:
            a, b = (Path(new) / name).read_bytes(), (Path(old) / name).read_bytes()
            assert a == (stage / name).read_bytes(), name
            assert (a != b) == (name in changed), name
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_name(out.name + '.sha256').write_text(f'{digest}  {out.name}\n')
    print(f'{out}: {len(names)} files, {out.stat().st_size} bytes, '
          f'SHA-256 {digest}\n  changed: {", ".join(sorted(changed))}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dist', type=Path, default=ROOT.parents[1] / 'dist')
    parser.add_argument('--force', action='store_true', help='replace an existing archive')
    args = parser.parse_args()
    pins = {name: digest for digest, name in (line.split() for line in
            (ROOT / 'inputs.sha256').read_text().splitlines() if line.strip() and not line.startswith('#'))}
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == pins[SOURCE.name], \
        f'{SOURCE} differs from inputs.sha256'
    # The current release build (make dist builds it first): never a VERIFY or developer
    # build, never a stale one.
    slave = (BUILD / 'F1GP.Slave').read_bytes()
    meta = json.loads((BUILD / 'build.json').read_text())
    assert meta['build'] == 'release', 'build'
    assert meta['slave_sha256'] == hashlib.sha256(slave).hexdigest(), 'stale build.json'
    assert meta['source_sha256'] == hashlib.sha256((ROOT / 'src/F1GP.s').read_bytes()).hexdigest(), \
        'stale build: make slave'
    assert b'Enhanced frame rate' in slave and b'Developer - ' not in slave, 'build'
    assert b'C3:' not in slave and b'C5:' not in slave and b'VERIFY' not in slave, 'build'
    version, date = re.search(rb'\$VER: ' + SLAVE.encode() + rb' ([0-9.a-z]+) \(([0-9.]+)\)',
                              slave).groups()
    assert version.decode() == version_of(BUILD / 'F1GP.Slave'), 'version'
    stamp = date_of(BUILD / 'F1GP.Slave')
    readme = (ROOT / 'release/ReadMe').read_bytes()
    assert b'Version ' + version + b' (' + date + b')' in readme, 'ReadMe entry'
    assert b'Version:  ' + version + b'\n' in readme, 'ReadMe header'
    assert b'Short:    Formula One Grand Prix Enhanced V' + version + b'\n' in readme, 'ReadMe Short'
    dist = args.dist.resolve()
    dist.mkdir(parents=True, exist_ok=True)
    out = dist / f'FormulaOneGrandPrixEnhanced-{version.decode()}-{stamp}.lha'
    if out.exists() and not args.force:
        raise SystemExit(f'{out} exists (FORCE=1 replaces it)')
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as stage:
        stage = Path(stage)
        extract(SOURCE, stage)
        names = members(SOURCE)
        changed = {f'{TOP}/{SLAVE}', f'{TOP}/ReadMe'} | {f'{TOP}/FormulaOneGrandPrix.{s}' for s in ICONS}
        assert changed <= set(names), sorted(changed - set(names))
        (stage / TOP / SLAVE).write_bytes(slave)
        (stage / TOP / 'ReadMe').write_bytes(readme)
        for s in ICONS:
            icon = stage / TOP / f'FormulaOneGrandPrix.{s}'
            icon.write_bytes(enhanced_icon(icon.read_bytes()))
        archive(stage, names, out, changed)


if __name__ == '__main__':
    main()
