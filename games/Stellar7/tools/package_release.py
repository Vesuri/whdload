#!/usr/bin/env python3
"""Build the installer archive from the untouched supplied archive.

    make dist        (game.sh game_dist; --dist names the output directory)

Output: DIST/Stellar7Enhanced-<version>-<YYYYMMDD>.lha and its .sha256, named from the
release slave's $VER string (docs/releasing.md), which the ReadMe's title and history entry
repeat. The archive ships the one release slave, Stellar7.slave, with both simulations.
"""
import argparse
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import release_payloads

ROOT = Path(__file__).resolve().parents[1]
# The shared packager's version_of and date_of; it has this module's name, so load it by path.
_spec = importlib.util.spec_from_file_location(
    'shared_package_release', ROOT.parents[1]/'common/tools/package_release.py')
shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(shared)


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Installer template changed: ' + repr(old))
    return text.replace(old, new, 1)


def check_installer(text):
    """Check balanced expressions without treating comments/strings as code."""
    depth = 0
    quoted = escaped = comment = False
    for c in text:
        if comment:
            if c == '\n':
                comment = False
        elif quoted:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                quoted = False
        elif c == ';':
            comment = True
        elif c == '"':
            quoted = True
        elif c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            assert depth >= 0, 'Unexpected closing parenthesis'
    assert depth == 0 and not quoted, 'Unclosed Installer expression/string'
    definitions = set(re.findall(r'\(procedure\s+(P_\w+)', text))
    calls = set(re.findall(r'\((P_\w+)\b', text))
    assert calls <= definitions, calls-definitions


def inventory(folder):
    return {str(p.relative_to(folder)): p.read_bytes()
            for p in folder.rglob('*') if p.is_file()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dist', type=Path, default=ROOT.parents[1]/'dist')
    args = ap.parse_args()
    os.chdir(ROOT)
    original = ROOT/'tmp/archives/Stellar7.lha'
    lha = os.environ.get('LHA') or shutil.which('lha')
    if not lha or not original.is_file():
        raise SystemExit('Need LHa for UNIX and tmp/archives/Stellar7.lha (make unpack).')
    out = args.dist.resolve()
    out.mkdir(parents=True, exist_ok=True)
    with (ROOT/'tmp/rate-matrix.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with (ROOT/'tmp/dist-build.log').open('w') as log:
            subprocess.run(['make', 'slave', 'VERIFY_FLAGS=', 'SIM68000_SUBSTEPS=3'],
                           check=True, stdout=log, stderr=subprocess.STDOUT)
        with tempfile.TemporaryDirectory(prefix='package-', dir=ROOT/'tmp') as scratch:
            scratch = Path(scratch)
            stage, unpacked = scratch/'stage', scratch/'unpacked'
            stage.mkdir(); unpacked.mkdir()
            subprocess.run([lha, 'xq2', str(original)], cwd=stage, check=True)
            baseline = inventory(stage)
            folder = stage/'Stellar7HD'
            builds = {'Stellar7.slave': 'Stellar7.Slave'}
            release = ROOT/'tmp/build/release'
            # Both simulations must be the development slaves' code (tools/release_payloads.py).
            release_payloads.check(release)
            version, stamp = shared.version_of(release/'Stellar7.Slave'), shared.date_of(release/'Stellar7.Slave')
            date = f'{stamp[6:]}.{stamp[4:6]}.{stamp[:4]}'
            for target, source in builds.items():
                if f'$VER: {target} {version} ({date})'.encode() not in (release/source).read_bytes():
                    raise ValueError(f'{source}: $VER does not name {target}')
            archive = out/f'Stellar7Enhanced-{version}-{stamp}.lha'
            for target, source in builds.items():
                data = (ROOT/'tmp/build/release'/source).read_bytes()
                assert b'WHDLOADS' in data
                for forbidden in (b'Movement and firing fixture', b'Deterministic menu fixture'):
                    assert forbidden not in data, 'VERIFY build cannot be packaged'
                (folder/target).write_bytes(data)
            assert b'C1:B:Fixed-rate simulation (15 Hz on 68000, 60 Hz on 68020+);' in (folder/'Stellar7.slave').read_bytes()
            script_path = folder/'Install-Stellar7'
            script = script_path.read_bytes().decode('latin1')
            # The conversion is validated only for the supplied English NTSC game.
            script = replace_once(script, '(set #multiple-versions ">")', '(set #multiple-versions "")')
            selection = '''(P_SelectVersion)
(set #sim-choice
  (askchoice
    (prompt "Stellar 7 Enhanced: choose the game timing.")
    (choices "Fixed-rate simulation (15 Hz on 68000, 60 Hz on 68020+)" "Original timing")
    (default 0)
    (help "The fixed-rate simulation keeps real-time game speed on every CPU; the slave picks the rate from the CPU. CUSTOM1=1 in the icon enables it. Original timing leaves it disabled.")
  )
)
'''
            script = replace_once(script, '(P_SelectVersion)\n', selection)
            script = replace_once(script, '  (P_SelectIcon)\n)', '''  (P_SelectIcon)
  (if (= #sim-choice 0)
    (tooltype
      (dest (tackon #dest #icon_prefix))
      (settooltype "CUSTOM1" "1")
    )
  )
)''')
            check_installer(script)
            script_path.write_bytes(script.encode('latin1'))
            readme = folder/'ReadMe'
            text = readme.read_bytes().decode('latin1')
            text = replace_once(text, 'Short : HD-Installer for Stellar 7',
                                'Short : Stellar 7 Enhanced HD-Installer')
            text = replace_once(text, '\xa9 1991 Dynamix\n',
                                f'\xa9 1991 Dynamix\nStellar 7 Enhanced {version} ({date})\n')
            text = text.replace('It supports 3 disks english and 2 disks german version.',
                                'This install supports the 3-disk English NTSC version only.')
            text = text.replace('WHDLoad 16+', 'WHDLoad 17+ (built with KickEmu 20.0)')
            text = text.replace('512 MB OtherMem', '512 KB OtherMem')
            note = f'''Version {version} ({date}) by Vesuri:
 - New fixed-rate simulation keeps the game at the same speed on every CPU:
   15 Hz on 68000/68010 and 60 Hz on 68020+, chosen from the CPU. The screen
   redraws as fast as the machine allows. CUSTOM1=1 enables it; without it
   the game keeps its original timing.
 - The installer asks which timing to use and sets CUSTOM1 in the icon.
 - Requires WHDLoad 17 (built with KickEmu 20.0).

Install using Install-Stellar7 on an Amiga with Installer and your original
English NTSC disks. Existing destination handling is inherited from the original
installer: preserve saves before choosing to delete an existing installation.
WHDLoad and Kickstart requirements below apply. For an already installed English
NTSC game, replace its Stellar7.slave with this one and add CUSTOM1=1 to the
game icon. The installer script has structural checks; its new choice UI has not
been run under Amiga Installer.

'''
            text = replace_once(text, 'Version 1.0 (02.01.2008) by Psygore:', note+'Version 1.0 (02.01.2008) by Psygore:')
            readme.write_bytes(text.encode('latin1'))
            expected = inventory(stage)
            changed = {'Stellar7HD/Install-Stellar7', 'Stellar7HD/ReadMe', 'Stellar7HD/Stellar7.slave'}
            assert set(expected) == set(baseline)
            assert {p for p in baseline if baseline[p] != expected[p]} == changed
            temporary = scratch/'installer.lha'
            subprocess.run([lha, 'a1o5q2', str(temporary), 'Stellar7HD', 'Stellar7HD.info'], cwd=stage, check=True)
            subprocess.run([lha, 'tq2', str(temporary)], check=True)
            subprocess.run([lha, 'xq2', str(temporary)], cwd=unpacked, check=True)
            assert inventory(unpacked) == expected, 'Extracted archive differs from staging'
            shutil.copyfile(temporary, archive)
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            (out/f'{archive.name}.sha256').write_text(f'{digest}  {archive.name}\n')
            print(archive)
            print(f'Archive integrity and all {len(expected)} extracted files verified '
                  f'({archive.stat().st_size} bytes).')


if __name__ == '__main__':
    main()
