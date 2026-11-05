#!/usr/bin/env python3
"""F6: a game directory with an F1GP-Ed datafile for the slave's local speed factors.

  python3 tools/f6_game.py OUT [--base N] [CIRCUIT=FACTOR ...]

OUT (under tmp/) gets a copy of the verified stock game directory. Its data/F1GP-Ed.f1gp
is F1GP-Ed's supplied 2002.f1gp (pinned in its archive, tmp/f1ed) with every Local Speed
Factor (+$1700 + 2 * circuit, circuits 0-15 in the game's order: 7 is Great Britain) set
to 0 (unset) except the CIRCUIT=FACTOR pairs. --base N also writes N as the game file's
Speed Factor (the base at h0+$29A7E), as F1GP-Ed's Team window does.
"""
import argparse
import hashlib
import shutil
import struct
from pathlib import Path

from f1_diff import hunks
from slave_inputs import ROOT, verify

STOCK = ROOT/'tmp/game/FormulaOneGrandPrix4Disk'
DATAFILE = ROOT/'tmp/f1ed/F1GP-Ed/2002.f1gp'
FACTORS = 0x1700
DATAFILE_SHA256 = '2e310d945b3fd21fda118f9aac7229c530ac550ccf8170b457b87874e4204abc'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out')
    parser.add_argument('--base', type=int)
    parser.add_argument('factors', nargs='*')
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if not out.is_relative_to(ROOT/'tmp'):
        raise ValueError('output must stay in project tmp/')
    verify()
    data = bytearray(DATAFILE.read_bytes())
    if hashlib.sha256(data).hexdigest() != DATAFILE_SHA256:
        raise ValueError(f'{DATAFILE} differs from its pinned SHA-256')
    data[FACTORS:FACTORS+32] = bytes(32)
    for item in args.factors:
        circuit, factor = map(int, item.split('='))
        assert 0 <= circuit < 16 and 0 <= factor < 65536
        struct.pack_into('>H', data, FACTORS+2*circuit, factor)
    shutil.copytree(STOCK, out)
    (out/'data/F1GP-Ed.f1gp').write_bytes(data)
    if args.base is not None:
        game = bytearray((out/'data/f1gp').read_bytes())
        h0 = {h: o for h, o, _ in hunks(bytes(game))}[0]
        struct.pack_into('>H', game, h0+0x29a7e, args.base)
        (out/'data/f1gp').write_bytes(game)
    print(f'{out.relative_to(ROOT)}: factors {args.factors or "none"}, base {args.base or "stock"}')


if __name__ == '__main__':
    main()
