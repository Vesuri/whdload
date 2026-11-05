#!/usr/bin/env python3
"""Build an experimental installer snapshot from the untouched supplied archive.

    make dist        (game.sh game_dist; --dist names the output directory)
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


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
    revision = subprocess.check_output(['git', 'rev-parse', '--short=12', 'HEAD'], text=True).strip()
    # Only this game's files: other games' work in progress does not make this build dirty.
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal', '--', '.']))
    build_id = revision + ('-dirty' if dirty else '')
    out = args.dist.resolve()
    out.mkdir(parents=True, exist_ok=True)
    archive = out/f'Stellar7_{build_id}_experimental_install.lha'
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
            builds = {'Stellar7.slave': 'Stellar7.Slave',
                      'Stellar7-Sim68000.Slave': 'Stellar7-Sim68000.Slave',
                      'Stellar7-Sim60.Slave': 'Stellar7-Sim60.Slave'}
            for target, source in builds.items():
                data = (ROOT/'tmp/build/release'/source).read_bytes()
                assert b'WHDLOADS' in data
                for forbidden in (b'Movement and firing fixture', b'Deterministic menu fixture'):
                    assert forbidden not in data, 'VERIFY build cannot be packaged'
                (folder/target).write_bytes(data)
            for name, rate in [('Stellar7-Sim68000.Slave', '15'), ('Stellar7-Sim60.Slave', '60')]:
                assert ('Experimental '+rate+' Hz simulation').encode() in (folder/name).read_bytes()
            script_path = folder/'Install-Stellar7'
            script = script_path.read_bytes().decode('latin1')
            # The conversion is validated only for the supplied English NTSC game.
            script = replace_once(script, '(set #multiple-versions ">")', '(set #multiple-versions "")')
            selection = '''(P_SelectVersion)
(set #sim-choice
  (askchoice
    (prompt "Stellar 7 experimental build: choose your CPU / timing.")
    (choices "68000/68010: 15 Hz" "68020 or faster: 60 Hz" "Original timing (development loader)")
    (default 0)
    (help "Both fixed-rate builds preserve real-time game speed. Playtesting is incomplete. Original timing leaves the conversion disabled.")
  )
)
(select #sim-choice
  (set #prefix-slave "Stellar7-Sim68000")
  (set #prefix-slave "Stellar7-Sim60")
  (set #prefix-slave "Stellar7")
)
'''
            script = replace_once(script, '(P_SelectVersion)\n', selection)
            script = replace_once(script, '  (P_SelectIcon)\n)', '''  (P_SelectIcon)
  (if (< #sim-choice 2)
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
            text = text.replace('It supports 3 disks english and 2 disks german version.',
                                'This experimental snapshot supports the 3-disk English NTSC version only.')
            text = text.replace('WHDLoad 16+', 'WHDLoad 17+ (built with KickEmu 20.0)')
            text = text.replace('512 MB OtherMem', '512 KB OtherMem')
            note = f'''Experimental source snapshot {build_id}

 - Fixed real-time simulation: 15 Hz for 68000/68010, 60 Hz for 68020+.
 - Rendering is independent, without interpolation; display-buffer reuse fix included.
 - Installer offers both CPU builds and the original-timing development loader.
 - Fixed-rate icons enable CUSTOM1=1. The selected rate never switches at runtime.
 - No VERIFY pilots, game data, Kickstart ROM or WHDLoad executable is included.
 - Physical controls, sound, pace and broader encounter playtesting remain open.
   This is a playtest package, not a declaration that step 6 is complete.

Install using Install-Stellar7 on an Amiga with Installer and your original
English NTSC disks. Choose the rate matching your CPU. Existing destination
handling is inherited from the original installer: preserve saves before choosing
to delete an existing installation. WHDLoad and Kickstart requirements below apply.
For an already installed English NTSC game, copy the chosen Sim slave beside
its data drawer, set the game icon SLAVE to that filename and add CUSTOM1=1.
The installer script has structural checks; its new choice UI has not been run
under Amiga Installer. Archive integrity and extracted contents are verified.

'''
            text = replace_once(text, 'Version 1.0 (02.01.2008) by Psygore:', note+'Version 1.0 (02.01.2008) by Psygore:')
            readme.write_bytes(text.encode('latin1'))
            expected = inventory(stage)
            changed = {'Stellar7HD/Install-Stellar7', 'Stellar7HD/ReadMe', 'Stellar7HD/Stellar7.slave'}
            added = {'Stellar7HD/Stellar7-Sim68000.Slave', 'Stellar7HD/Stellar7-Sim60.Slave'}
            assert set(expected) == set(baseline) | added
            assert {p for p in baseline if baseline[p] != expected[p]} == changed
            temporary = scratch/'installer.lha'
            subprocess.run([lha, 'a1o5q2', str(temporary), 'Stellar7HD', 'Stellar7HD.info'], cwd=stage, check=True)
            subprocess.run([lha, 'tq2', str(temporary)], check=True)
            subprocess.run([lha, 'xq2', str(temporary)], cwd=unpacked, check=True)
            assert inventory(unpacked) == expected, 'Extracted archive differs from staging'
            shutil.copyfile(temporary, archive)
            report = dict(build_id=build_id, experimental=True, archive=archive.name,
                          sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                          bytes=archive.stat().st_size, changed=sorted(changed), added=sorted(added),
                          preserved_original_members=len(baseline)-len(changed),
                          installer_runtime_tested=False,
                          members={p: hashlib.sha256(data).hexdigest() for p, data in sorted(expected.items())})
            archive.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
            archive.with_suffix('.sha256').write_text(report['sha256']+'  '+archive.name+'\n')
            print(archive)
            print(f'Archive integrity and all {len(expected)} extracted files verified ({report["bytes"]} bytes).')


if __name__ == '__main__':
    main()
