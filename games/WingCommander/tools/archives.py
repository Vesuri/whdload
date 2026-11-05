"""The original archives: pinned in inputs.sha256, installed by make unpack in tmp/archives/.

verified(name) checks an archive against its pin before a tool reads it.
"""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Psygore's installer and the two pre-installed WHDLoad drawers.
NAMES = {'installer': 'WingCommander.lha',
         'cd32': 'WingCommander_v1.0_CD32.lha',
         'ocs': 'WingCommander_v1.0_1657.lha'}


def pinned():
    """inputs.sha256 as {file name: sha256}."""
    pins = {}
    for line in (ROOT/'inputs.sha256').read_text().splitlines():
        if line.strip() and not line.startswith('#'):
            digest, name = line.split(None, 1)
            pins[name.strip()] = digest
    return pins


def verified(name):
    """tmp/archives/<archive> for 'installer', 'cd32' or 'ocs', checked against its pin."""
    filename = NAMES[name]
    path = ROOT/'tmp/archives'/filename
    if not path.is_file():
        raise ValueError(f'missing tmp/archives/{filename}: make unpack ARCHIVES=<directory>')
    if hashlib.sha256(path.read_bytes()).hexdigest() != pinned()[filename]:
        raise ValueError(f'checksum mismatch: {filename}; original retained')
    return path
