#!/usr/bin/env python3
"""Package the release (make dist, game.sh game_dist): common/tools/package_release.py,
driven by release/release.json, with a version pattern for this slave.

The slave names itself in several words ("$VER: Hard Drivin' WHDLoad Slave 4.0b (date)"),
which the shared pattern ("$VER: <one word> <version>") does not read; here the version is
the word before the date.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
import package_release  # noqa: E402


def version_of(slave):
    m = re.search(rb'\$VER: [^\x00]*? (\d[^\s\x00]*) \(', slave.read_bytes())
    if not m:
        sys.exit(f'{slave}: no "$VER: <name> <version> (<date>)" string')
    return m.group(1).decode('latin-1')


package_release.version_of = version_of

if __name__ == '__main__':
    package_release.main()
