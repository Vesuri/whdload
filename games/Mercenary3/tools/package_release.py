"""Repack the WHDLoad installer archive with the new slave and ReadMe -> the repository's dist/.

    make dist [FORCE=1]          (game.sh game_dist: --dist DIST [--force])

Input: tmp/archives/Mercenary3.lha (pinned in manifest/inputs.json). Output:
DIST/Mercenary3Enhanced-<version>-<YYYYMMDD>.lha, from the slave's $VER string (docs/releasing.md),
and its .sha256; an existing archive is replaced only with --force. The slave, the ReadMe
and the two game icons (Mercenary3.inf and Mercenary3.romicon, which gain the tooltype
CUSTOM5=1 so Enhanced framerate starts checked) are replaced, and the source drawer holds
exactly the src/ files the release slave was assembled from (its .deps, beside the slave),
under the shipped names where they exist (docs/releasing.md); every other member is the
original's.
The ReadMe is the WHDLoad Install Template's (pinned in manifest/release-templates.json)
with release/readme-body.txt and the original ReadMe's version 1.2 history entry.
LHA names LHa for UNIX; Lhasa cannot create archives.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile

from check_inputs import main as check_inputs

ROOT = Path(__file__).resolve().parents[1]
# The shared packager's version_of and date_of; it has this module's name, so load it by path.
_spec = importlib.util.spec_from_file_location(
    'shared_package_release', ROOT.parents[1] / 'common/tools/package_release.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)
SOURCE = ROOT / 'tmp/archives/Mercenary3.lha'
TOP = 'Mercenary3 Install'
SLAVE = f'{TOP}/Mercenary3.Slave'
README = f'{TOP}/ReadMe'
ICONS = [f'{TOP}/Mercenary3.inf', f'{TOP}/Mercenary3.romicon']
SRC = f'{TOP}/src'


def true_case(rel):
    """rel (under the game directory) in the spelling its directory entries have."""
    path = ROOT
    for part in Path(rel).parts:
        names = {n.lower(): n for n in os.listdir(path)}
        path = path / names.get(part.lower(), part)
    return path.relative_to(ROOT).as_posix()


def release_sources(slave, shipped):
    """Archive member -> game file for each src/ file the slave's build read.

    A file keeps a shipped member's name when one matches it ignoring case; shipped
    sources the build did not read are dropped.
    """
    deps = slave.with_suffix('.deps')
    if not deps.is_file():
        raise ValueError(f'no {deps}: the release build lists its sources there')
    by_case = {m.lower(): m for m in shipped}
    wanted = {}
    for dep in deps.read_text().split():
        dep = true_case(dep)
        if not dep.startswith('src/'):
            raise ValueError(f'the slave is built from {dep}, outside src/')
        member = f'{SRC}/{dep[len("src/"):]}'
        wanted[by_case.get(member.lower(), member)] = ROOT / dep
    return wanted


def members(archive):
    return subprocess.run(['lsar', str(archive)], capture_output=True, text=True,
                          check=True).stdout.splitlines()[1:]


def extract(lha, archive, into):
    subprocess.run([lha, f'xqw={into}', str(archive)], check=True)


def enhanced_icon(original):
    """Append CUSTOM5=1 to a game icon's tooltype array.

    Locate the length-prefixed WHDLoad default tool, then walk and validate the whole
    array; its stored size includes the terminating null pointer. Appending keeps the
    ROMIcon colour marker first. Image data and any bytes after the array are kept.
    """
    assert original[:2] == b'\xe3\x10'
    found = [i for m in (b'\x00\x00\x00\x08WHDLOAD\x00', b'\x00\x00\x00\x08WHDLoad\x00')
             for i in [original.find(m)] if i >= 0]
    assert len(found) == 1
    start = found[0] + 12
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
    assert b'SLAVE=MERCENARY3.SLAVE' in entries
    assert not any(value.lstrip(b'(').startswith(b'CUSTOM5=') for value in entries)
    entry = b'CUSTOM5=1\0'
    addition = struct.pack('>I', len(entry)) + entry
    updated = (original[:start] + struct.pack('>I', size + 4) + original[start + 4:cursor]
               + addition + original[cursor:])
    # Removing the addition must give back every original byte, artwork included.
    assert (updated[:start] + struct.pack('>I', size) + updated[start + 4:cursor]
            + updated[cursor + len(addition):]) == original
    return updated


def template_readme():
    whdload = Path(os.environ['WHDLOAD'])
    pins = json.loads((ROOT / 'manifest/release-templates.json').read_text())
    name = 'Install Template/Xxx Install/ReadMe'
    data = (whdload / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != pins[name]:
        raise ValueError(f'WHDLoad template differs: {name}')
    return data.decode('latin-1')


def readme(version, original):
    text = template_readme()
    start = text.index(' This install applies to ')
    end = text.index(' Contact:')
    body = (ROOT / 'release/readme-body.txt').read_text(encoding='utf-8')
    if f' version {version} (' not in body:
        raise ValueError(f'release/readme-body.txt has no version {version} entry')
    old = original.decode('latin-1')
    history = old[old.index('\tversion 1.2 '):].replace('\t', ' ').rstrip()
    text = text[:start] + body + '\n' + history + '\n\n\n' + text[end:]
    return text.encode('latin-1')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--slave', type=Path, default=ROOT / 'tmp/build/release/Mercenary3.Slave')
    parser.add_argument('--dist', type=Path, default=ROOT.parents[1] / 'dist')
    parser.add_argument('--force', action='store_true', help='replace an existing archive')
    args = parser.parse_args()
    lha = os.environ['LHA']
    check_inputs()
    slave = args.slave.read_bytes()
    if b'(VERIFY)' in slave:
        raise ValueError('VERIFY build; package the release slave')
    version, stamp = shared.version_of(args.slave), shared.date_of(args.slave)
    date = f'{stamp[6:]}.{stamp[4:6]}.{stamp[:4]}'
    # The splash window's version (ws_info) must agree with $VER.
    if f'Version {version} ({date})'.encode() not in slave:
        raise ValueError(f'ws_info lacks "Version {version} ({date})"')
    body = (ROOT / 'release/readme-body.txt').read_text()
    if f' version {version} ({date}) ' not in body:
        raise ValueError(f'ReadMe entry for version {version} ({date}) is missing')
    if f' Mercenary 3 Enhanced {version} ({date})\n' not in body:
        raise ValueError(f'ReadMe lacks the title "Mercenary 3 Enhanced {version} ({date})"')

    names = members(SOURCE)
    changed = {SLAVE, README, *ICONS}
    if not changed <= set(names):
        raise ValueError('Source archive lacks the slave, ReadMe or game icons')
    shipped = {m for m in names if m.startswith(SRC + '/')}
    if not shipped:
        raise ValueError(f'Source archive ships no {SRC}/')
    sources = release_sources(args.slave, shipped)
    removed = shipped - set(sources)
    added = set(sources) - set(names)
    changed |= set(sources)
    final = [m for m in names if m not in removed] + sorted(added)
    dist = args.dist.resolve()
    dist.mkdir(parents=True, exist_ok=True)
    out = dist / f'Mercenary3Enhanced-{version}-{stamp}.lha'
    digest_file = dist / f'{out.name}.sha256'
    if out.exists() and not args.force:
        raise ValueError(f'{out} exists (FORCE=1 replaces it)')
    with tempfile.TemporaryDirectory(dir=ROOT / 'tmp') as tmp:
        stage, new, old = (Path(tmp) / d for d in ('stage', 'new', 'old'))
        extract(lha, SOURCE, stage)
        (stage / SLAVE).write_bytes(slave)
        (stage / README).write_bytes(readme(version, (stage / README).read_bytes()))
        for name in ICONS:
            (stage / name).write_bytes(enhanced_icon((stage / name).read_bytes()))
        for name in removed:
            (stage / name).unlink()
        for name, path in sources.items():
            (stage / name).parent.mkdir(parents=True, exist_ok=True)
            (stage / name).write_bytes(path.read_bytes())
        out.unlink(missing_ok=True)
        digest_file.unlink(missing_ok=True)
        subprocess.run([lha, 'a1o5q2', str(out), *final], cwd=stage, check=True)

        test = subprocess.run([lha, 't', str(out)], capture_output=True, text=True)
        if test.returncode:
            raise ValueError(test.stdout + test.stderr)
        # LHa for UNIX sorts members, so compare sorted lists.
        if sorted(members(out)) != sorted(final):
            raise ValueError('Member list differs from the expected one')
        extract(lha, out, new)
        extract(lha, SOURCE, old)
        for name in final:
            a = (new / name).read_bytes()
            if a != (stage / name).read_bytes():
                raise ValueError(f'Extracted member differs from staging: {name}')
            if name in added:
                continue
            # Replaced sources may happen to equal the original; everything else must not.
            if (a != (old / name).read_bytes()) != (name in changed) and name not in sources:
                raise ValueError(f'Unexpected change state: {name}')
        for path, expected in ((new, set(final)), (old, set(names))):
            extra = {p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}
            if extra != expected:
                raise ValueError(f'Extraction holds other files: {sorted(extra ^ expected)}')
    digest_file.write_text(f'{hashlib.sha256(out.read_bytes()).hexdigest()}  {out.name}\n')
    print(f'{os.path.relpath(out, ROOT)}: {len(final)} files, {out.stat().st_size} bytes; '
          f'changed: {", ".join(sorted(changed - added))}; added: {", ".join(sorted(added))}; '
          f'removed: {", ".join(sorted(removed))}')


if __name__ == '__main__':
    main()
