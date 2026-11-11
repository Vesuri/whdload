"""Repack a game's original release archives with the new slaves -> dist/ (ignored).

    common/dist.sh            (make dist)

Driven by the game's release/release.json:

    {
      "archives": [
        {
          "input": "TheirFinestHour.lha",
          "output": "TheirFinestHourEnhanced-{version}-{date}.lha",
          "replace": {
            "TheirFinestHour/TheirFinestHour.Slave": "build:TheirFinestHour",
            "TheirFinestHour/ReadMe": "release/ReadMe"
          },
          "add": {},
          "remove": [],
          "source": {"dir": "TheirFinestHour/src", "variants": ["TheirFinestHour"]}
        }
      ]
    }

- input: a file named in inputs.sha256, taken from tmp/archives/.
- output: the file name in dist/; {version} is the release version from the first replaced
  slave's $VER string: the word before its date ("$VER: Name.Slave 1.2b (date)" and
  "$VER: Name WHDLoad Slave 1.2b (date)" give 1.2b), else the word after a one-word name.
  {date} is that string's date as YYYYMMDD ("(05.11.2026)" gives 20261105). Releases are
  named <Game>Enhanced-{version}-{date}.lha (docs/releasing.md).
- replace / add: archive member -> "build:<Variant>" (that variant's release slave) or a
  path relative to the game directory. A replaced member must exist in the original and an
  added one must not. remove: members to drop.
- tooltypes (optional): icon member -> tooltypes added in front of the icon's own, so before
  any NewIcon image lines; images, the default tool and trailing ColorIcon or GlowIcon data
  stay as shipped. The icon must have tooltypes and none with the same name.
- source (optional): the archive's slave source drawer. Its files are replaced by exactly
  the game's src/ files the listed variants' release builds were assembled from (the .deps
  lists), keeping src/-relative paths in the files' own spelling (an include may name a
  file in another case). Only an archive that already ships source gets one. "keep" lists
  shipped members of the drawer that stay as shipped: the source of a binary the release
  does not change (an install imager), its makefile.

Checks: every replaced slave and ReadMe must differ from the original, a replaced ReadMe
must mention the version, the archive must pass `lha t`, and its extraction must hold
exactly the original members plus the added ones minus the removed ones, each equal to
the staged file and every untouched member byte-identical to the original.
"""
import argparse
import filecmp
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

LHA = os.environ.get('LHA', os.path.expanduser('~/.local/share/amiga/lha-compressor/src/lha'))


def files(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())


def extract(archive, into):
    into.mkdir(parents=True)
    subprocess.run([LHA, f'xqw={into}', str(archive)], check=True)


def version_of(slave):
    data = slave.read_bytes()
    m = (re.search(rb'\$VER: [^\x00\n(]*? (\d[^\s\x00]*) \(', data)
         or re.search(rb'\$VER: \S+ (\d[^\s\x00]*)', data))
    if not m:
        sys.exit(f'{slave}: no "$VER: <name> <version> (<date>)" string')
    return m.group(1).decode('latin-1')


def date_of(slave):
    """The $VER string's date, "(dd.mm.yyyy)", as YYYYMMDD."""
    m = re.search(rb'\$VER: [^\x00\n(]*? \d[^\s\x00]* \((\d{1,2})\.(\d{1,2})\.(\d{4})\)',
                  slave.read_bytes())
    if not m:
        sys.exit(f'{slave}: no "$VER: <name> <version> (dd.mm.yyyy)" date')
    day, month, year = (int(x) for x in m.groups())
    return f'{year:04d}{month:02d}{day:02d}'


def with_tooltypes(icon, entries, name):
    """icon (a .info DiskObject) with entries added in front of its tooltypes. Everything
    else stays byte for byte."""
    def fail(why):
        sys.exit(f'{name}: {why}')
    u16 = lambda at: struct.unpack_from('>H', icon, at)[0]
    u32 = lambda at: struct.unpack_from('>I', icon, at)[0]
    if len(icon) < 78 or icon[:2] != b'\xe3\x10':
        fail('not an icon')
    # DiskObject: the gadget's two image pointers at 22 and 26, then the default tool,
    # tooltypes and drawer data pointers at 50, 54 and 66. Then drawer data (56 bytes), the
    # images (20 bytes each and their planes), the default tool and the tooltype array.
    render, select = u32(22), u32(26)
    default_tool, tooltypes, drawer = u32(50), u32(54), u32(66)
    at = 78 + (56 if drawer else 0)
    for image in (render, select):
        if image:
            width, height, depth, data = u16(at + 4), u16(at + 6), u16(at + 8), u32(at + 10)
            at += 20 + ((width + 15) // 16 * 2 * height * depth if data else 0)
    if default_tool:
        at += 4 + u32(at)
    if not tooltypes:
        fail('has no tooltypes to add to')
    size, cursor, keys = u32(at), at + 4, []
    if size < 4 or size % 4:
        fail(f'tooltype array size {size}')
    for _ in range(size // 4 - 1):
        length = u32(cursor)
        value = icon[cursor + 4:cursor + 4 + length]
        if not length or len(value) != length or not value.endswith(b'\0'):
            fail('its tooltypes do not parse')
        keys.append(value.rstrip(b'\0').lstrip(b'(').split(b'=')[0].strip().upper())
        cursor += 4 + length
    insert = b''
    for entry in entries:
        key = entry.split('=')[0].strip()
        if key.upper().encode('latin-1') in keys:
            fail(f'already has a {key} tooltype')
        value = entry.encode('latin-1') + b'\0'
        insert += struct.pack('>I', len(value)) + value
    out = icon[:at] + struct.pack('>I', size + 4 * len(entries)) + insert + icon[at + 4:]
    if icon[:at] + struct.pack('>I', size) + out[at + 4 + len(insert):] != icon:
        fail('the insertion does not reverse')
    return out


def true_case(root, rel):
    """rel (a path under root) in the spelling the directory entries have. vasm reports an
    include as the source wrote it, which on a case-insensitive disk may differ."""
    path = root
    for part in Path(rel).parts:
        names = {n.lower(): n for n in os.listdir(path)}
        path = path / names.get(part.lower(), part)
    return str(path.relative_to(root))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game-root', required=True, type=Path)
    ap.add_argument('--dist', required=True, type=Path)
    ap.add_argument('--variants', required=True, help="the game's VARIANTS")
    ap.add_argument('--force', action='store_true', help='replace an existing dist file')
    args = ap.parse_args()
    root = args.game_root.resolve()
    variants = args.variants.split()
    spec = json.loads((root / 'release/release.json').read_text())
    build = root / 'tmp/build/release'
    args.dist.mkdir(parents=True, exist_ok=True)

    def source_of(value):
        if value.startswith('build:'):
            variant = value[len('build:'):]
            if variant not in variants:
                sys.exit(f'unknown variant {variant}; VARIANTS has {", ".join(variants)}')
            return build / f'{variant}.Slave'
        path = root / value
        if not path.is_file():
            sys.exit(f'no {value}')
        return path

    for entry in spec['archives']:
        original = root / 'tmp/archives' / entry['input']
        if not original.is_file():
            sys.exit(f'no tmp/archives/{entry["input"]}: run make unpack first')
        tmp = Path(tempfile.mkdtemp(prefix='dist.', dir=root / 'tmp'))
        try:
            orig_dir, stage = tmp / 'original', tmp / 'stage'
            extract(original, orig_dir)
            shutil.copytree(orig_dir, stage, symlinks=True)
            before = set(files(orig_dir))
            added, removed = set(), set()

            replace = entry.get('replace', {})
            slave_members = [m for m, v in replace.items() if v.startswith('build:')]
            if not slave_members:
                sys.exit(f'{entry["input"]}: replace names no build:<Variant> slave')
            first_slave = source_of(replace[slave_members[0]])
            version = version_of(first_slave)

            for member, value in replace.items():
                if member not in before:
                    sys.exit(f'{entry["input"]}: no member {member} to replace')
                shutil.copyfile(source_of(value), stage / member)
            for member, value in entry.get('add', {}).items():
                if member in before:
                    sys.exit(f'{entry["input"]}: {member} exists; replace it instead')
                (stage / member).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source_of(value), stage / member)
                added.add(member)
            for member in entry.get('remove', []):
                if member not in before:
                    sys.exit(f'{entry["input"]}: no member {member} to remove')
                (stage / member).unlink()
                removed.add(member)
            tooltypes = entry.get('tooltypes', {})
            for member, entries in tooltypes.items():
                if member not in before or member in replace or member in removed:
                    sys.exit(f'{entry["input"]}: {member} is not a shipped, kept and unreplaced icon')
                icon = stage / member
                icon.write_bytes(with_tooltypes(icon.read_bytes(), entries, member))

            source = entry.get('source')
            if source:
                drawer = source['dir'].rstrip('/')
                shipped = {m for m in before if m.startswith(drawer + '/')}
                if not shipped:
                    sys.exit(f'{entry["input"]}: ships no source in {drawer}/')
                keep = {f'{drawer}/{m}' for m in source.get('keep', [])}
                if keep - shipped:
                    sys.exit(f'{entry["input"]}: keep names no shipped {", ".join(sorted(keep - shipped))}')
                wanted = {}
                for variant in source['variants']:
                    deps = build / f'{variant}.deps'
                    if not deps.is_file():
                        sys.exit(f'no {deps.relative_to(root)}: the release build lists its sources there')
                    for dep in deps.read_text().split():
                        dep = true_case(root, dep)
                        if not dep.startswith('src/'):
                            sys.exit(f'{variant} is built from {dep}, outside src/; ship it by hand')
                        wanted[f'{drawer}/{dep[len("src/"):]}'] = root / dep
                if keep & set(wanted):
                    sys.exit(f'{entry["input"]}: the build replaces kept {", ".join(sorted(keep & set(wanted)))}')
                for member in shipped - set(wanted) - keep:
                    (stage / member).unlink()
                    removed.add(member)
                for member, path in wanted.items():
                    (stage / member).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(path, stage / member)
                    if member not in before:
                        added.add(member)

            for member, value in replace.items():
                if filecmp.cmp(orig_dir / member, stage / member, shallow=False):
                    sys.exit(f'{member} is identical to the original')
                if Path(member).name.lower() == 'readme' and version.encode() not in (stage / member).read_bytes():
                    sys.exit(f'{member} does not mention version {version}')

            fields = {'version': version}
            if '{date}' in entry['output']:
                fields['date'] = date_of(first_slave)
            out = args.dist / entry['output'].format(**fields)
            if out.exists() and not args.force:
                sys.exit(f'{out} exists (FORCE=1 replaces it)')
            for d in sorted((p for p in stage.rglob('*') if p.is_dir()), reverse=True):
                if not any(d.iterdir()):
                    d.rmdir()
            new = tmp / out.name
            names = sorted(p.name for p in stage.iterdir())
            subprocess.run([LHA, 'a1o5q2', str(new), *names], cwd=stage, check=True)
            test = subprocess.run([LHA, 't', str(new)], capture_output=True, text=True)
            if test.returncode:
                sys.exit(f'lha t failed:\n{test.stdout}{test.stderr}')

            check = tmp / 'check'
            extract(new, check)
            got = set(files(check))
            expected = (before | added) - removed
            if got != expected:
                sys.exit(f'members differ: missing {sorted(expected - got)}, extra {sorted(got - expected)}')
            for member in sorted(got):
                if not filecmp.cmp(check / member, stage / member, shallow=False):
                    sys.exit(f'{member} differs from the staged file')
            changed = set(replace) | set(tooltypes) | added | {m for m in got if source and m.startswith(source['dir'].rstrip('/') + '/')
                                               and m[len(source['dir'].rstrip('/')) + 1:] not in source.get('keep', [])}
            for member in sorted(got - changed):
                if not filecmp.cmp(check / member, orig_dir / member, shallow=False):
                    sys.exit(f'{member} changed but was not declared')

            shutil.move(str(new), out)
            digest = hashlib.sha256(out.read_bytes()).hexdigest()
            (out.parent / (out.name + '.sha256')).write_text(f'{digest}  {out.name}\n')
            print(f'{out}  (version {version}; replaced {len(replace)}, added {len(added)}, removed {len(removed)})')
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
