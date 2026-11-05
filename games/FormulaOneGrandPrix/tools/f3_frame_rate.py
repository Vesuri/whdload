#!/usr/bin/env python3
"""F3: a game directory whose f1gp carries only F1GP-Ed's frame-rate bytes.

    python3 tools/f3_frame_rate.py SAVED OUT

SAVED is an f1gp file F1GP-Ed saved (F1: tmp/f1/out/df-2002.f1gp). OUT (under tmp/) gets
a copy of the verified stock game directory whose data/f1gp is the stock file with the
ranges F1GP-Ed's Frames/sec and Target Display settings write (F1) taken from SAVED: the
pacer minimum and cadence tables h0+$125A-$1271 and the step words h0+$34362-$34369.
Every other setting stays stock, so the stock routes reach the race. Prints the steps.
"""
import shutil
import struct
import sys
from pathlib import Path

from f1_diff import hunks
from slave_inputs import ROOT, verify

STOCK = ROOT/'tmp/game/FormulaOneGrandPrix4Disk'
RANGES = ((0, 0x125a, 0x1272), (0, 0x34362, 0x3436a))


def main():
    saved, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
    if not out.is_relative_to(ROOT/'tmp'):
        raise ValueError('output must stay in project tmp/')
    verify()
    stock = (STOCK/'data/f1gp').read_bytes()
    edited = saved.read_bytes()
    if len(edited) != len(stock):
        raise ValueError('not a 582,992-byte f1gp file')
    layout = {h: (o, n) for h, o, n in hunks(stock)}
    assert layout == {h: (o, n) for h, o, n in hunks(edited)}
    data = bytearray(stock)
    for h, low, high in RANGES:
        start = layout[h][0]
        data[start+low:start+high] = edited[start+low:start+high]
    shutil.copytree(STOCK, out)
    (out/'data/f1gp').write_bytes(data)
    h0 = layout[0][0]
    words = struct.unpack_from('>4H', data, h0+0x34362)
    print(f'{out.relative_to(ROOT)}: pacer minimum {struct.unpack_from(">H", data, h0+0x125a)[0]}, '
          f'half step {words[0]}, steps {words[1:]}; 65536/step = {65536/words[2]:.3f} Hz')


if __name__ == '__main__':
    main()
