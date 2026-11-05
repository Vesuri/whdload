#!/usr/bin/env python3
"""Rebuild Psygore's v1.1 installer archive with the new slave -> dist/ (LH5, level-1 headers).

    make dist        (game.sh game_dist; --dist names the output directory, default the
                      repository's dist/)

Input, kept local in tmp/archives/ (make unpack; never committed): the installer
TheirFinestHour.lha. Output, with its .sha256 beside it:

  dist/TheirFinestHourEnhanced-<version>-<YYYYMMDD>.lha   the same members as TheirFinestHour.lha

<version> and <YYYYMMDD> come from the slave's $VER string (common/tools/package_release.py
version_of, date_of). Changed members are the six game launch icons (CUSTOM2=1), the freshly
built slave, the template-based ReadMe and Install-TheirFinestHour. Everything else is copied
byte for byte; the archive is re-extracted and checked member by member against its source.
Only the installer package ships, never the preinstalled game (docs/releasing.md). LHA names
LHa for UNIX (Lhasa, the usual `lha`, cannot create archives).
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import os
import subprocess
import struct
import tempfile

from install_package import readme, installer

ROOT = Path(__file__).resolve().parents[1]
# The shared packager's $VER rules (this file shares its module name, so load it by path).
_spec = importlib.util.spec_from_file_location(
    'common_package_release', ROOT.parents[1] / 'common/tools/package_release.py')
_common = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_common)
version_of, date_of = _common.version_of, _common.date_of

LHA = os.environ.get('LHA', os.path.expanduser('~/.local/share/amiga/lha-compressor/src/lha'))
SOURCE = ROOT / 'tmp/archives/TheirFinestHour.lha'
TOP, SLAVE = 'TheirFinestHourHD', 'TheirFinestHour.slave'
ICONS = ('inf', 'newicon', 'colicon', 'colicon2', 'colbox', 'colbox2')


def members(archive):
    return subprocess.run(['lsar', archive], capture_output=True, text=True,
                          check=True).stdout.splitlines()[1:]


def extract(archive, into):
    subprocess.run(['lha', f'xqw={into}', str(archive)], check=True)


def enhanced_icon(original):
    """Add CUSTOM2=1 to these source archives' classic/NewIcon/ColorIcon launchers.

    Locate their length-prefixed WHDLoad default tool, then validate the whole
    tooltype array. Preserve image data, padding and trailing ColorIcon chunks.
    The stored array size includes the terminating null pointer.
    """
    marker = b'\x00\x00\x00\x08WHDLoad\x00'
    assert original[:2] == b'\xe3\x10' and original.count(marker) == 1
    start = original.index(marker) + len(marker)
    size = struct.unpack_from('>I', original, start)[0]
    assert size >= 4 and size % 4 == 0
    cursor = start + 4
    entries = []
    for _ in range(size // 4 - 1):
        length = struct.unpack_from('>I', original, cursor)[0]
        cursor += 4
        value = original[cursor:cursor + length]
        assert length and len(value) == length and value.endswith(b'\0')
        entries.append(value.rstrip(b'\0').upper())
        cursor += length
    assert b'SLAVE=THEIRFINESTHOUR.SLAVE' in entries
    assert not any(value.lstrip(b'(').startswith(b'CUSTOM2=') for value in entries)
    entry = b'CUSTOM2=1\0'
    addition = struct.pack('>I', len(entry)) + entry
    updated = (original[:start] + struct.pack('>I', size + 4) + addition
               + original[start + 4:])
    # Reversing the insertion must reproduce every original byte, including artwork.
    assert (updated[:start] + struct.pack('>I', size)
            + updated[start + 4 + len(addition):]) == original
    return updated


def archive(stage, names, out, source, changed):
    out.unlink(missing_ok=True)
    subprocess.run([LHA, 'a1o5q2', str(out), *names], cwd=stage, check=True)
    test = subprocess.run([LHA, 't', str(out)], capture_output=True, text=True)
    assert test.returncode == 0, test.stdout + test.stderr
    assert sorted(members(out)) == sorted(names), out  # LHa for UNIX sorts the members
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as new, tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as old:
        extract(out, new)
        extract(source, old)
        for name in names:
            a, b = (Path(new) / name).read_bytes(), (Path(old) / name).read_bytes()
            assert a == (stage / name).read_bytes(), name
            assert (a != b) == (name in changed), name
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_name(out.name + '.sha256').write_text(f'{digest}  {out.name}\n')
    print(f'{out}: {len(names)} files, {out.stat().st_size} bytes, SHA-256 {digest}\n'
          f'  changed: {", ".join(sorted(changed))}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dist', type=Path, default=ROOT.parents[1] / 'dist')
    dist = ap.parse_args().dist.resolve()
    (ROOT / 'tmp').mkdir(exist_ok=True)
    with (ROOT / 'tmp/dist-build.log').open('w') as log:
        subprocess.run(['make', 'slave'], cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT)
    slave_path = ROOT / 'tmp/build/release/TheirFinestHour.Slave'
    slave = slave_path.read_bytes()
    assert b'C5:' not in slave, 'VERIFY build'
    version, date = version_of(slave_path), date_of(slave_path)
    assert f'Version {version} '.encode() in (ROOT / 'release/readme-history.txt').read_bytes()
    dmy = f'{date[6:]}.{date[4:6]}.{date[:4]}'
    title = f'Their Finest Hour Enhanced {version} ({dmy})'
    dist.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as stage:
        stage = Path(stage)
        extract(SOURCE, stage)
        names = members(SOURCE)
        install_name = f'{TOP}/Install-TheirFinestHour'
        icons = [f'{TOP}/TheirFinestHour.{s}' for s in ICONS]
        changed = {f'{TOP}/{SLAVE}', f'{TOP}/ReadMe', install_name, *icons}
        assert changed <= set(names), sorted(changed - set(names))
        # Every launch icon style gets the tooltype; no other icon is a game launcher.
        assert sorted(icons) == sorted(n for n in names if n.startswith(f'{TOP}/TheirFinestHour.')
                                       and not n.endswith(('.slave', '.Slave'))), names
        (stage / TOP / SLAVE).write_bytes(slave)
        new_readme = readme((stage / TOP / 'ReadMe').read_bytes(), title)
        assert f' {title}\n'.encode() in new_readme
        (stage / TOP / 'ReadMe').write_bytes(new_readme)
        install = stage / install_name
        install.write_bytes(installer(install.read_bytes()))
        for name in icons:
            icon = stage / name
            icon.write_bytes(enhanced_icon(icon.read_bytes()))
        archive(stage, names, dist / f'TheirFinestHourEnhanced-{version}-{date}.lha', SOURCE, changed)


if __name__ == '__main__':
    main()
