#!/usr/bin/env python3
"""F1 write map: save F1GP-Ed 3.44 settings into copies of the f1gp file and collect them.

  python3 tools/f1_writemap.py OUT NAME [--new] [--datafile PATH] [--xor START LEN VALUE]

Boots amiga/ed.sh (Workbench 2.04, F1GP-Ed on DH0, a fresh copy of the pinned f1gp as
DH1:f1gp), optionally resets every setting (Project/New, Right-Amiga N), saves to the F1GP
binary (Right-Amiga B, confirmed with Left-Amiga V), waits for the file to change and copies
it to OUT/NAME.f1gp. Without --datafile F1GP-Ed loads 2002.f1gp, named by its icon's
DATAFILE tooltype. --xor saves a variant of the datafile (default 2002.f1gp) with VALUE
XORed into LEN bytes from START (F1's attribution runs). tools/f1_diff.py maps the
differences to hunk offsets.
"""
import argparse, filecmp, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1_ed  # noqa: E402  (the server and its commands)
from amigaxdev.input import Input  # noqa: E402

ROOT = f1_ed.ROOT
PINNED = os.path.join(ROOT, 'tmp/game/FormulaOneGrandPrix4Disk/data/f1gp')
EDITED = os.path.join(ROOT, 'amiga/.run/ed/dh1/f1gp')
R_AMIGA, L_AMIGA, KEY_N, KEY_B, KEY_V = 0x67, 0x66, 0x36, 0x35, 0x34


def chord(g, qualifier, key):
    with Input(g) as c:
        c.key(qualifier, True); c.key(key, True); c.fields(5)
        c.key(key, False); c.key(qualifier, False); c.fields(50)


def main():
    a = argparse.ArgumentParser()
    a.add_argument('out'); a.add_argument('name')
    a.add_argument('--new', action='store_true'); a.add_argument('--datafile')
    a.add_argument('--xor', nargs=3, type=lambda v: int(v, 0))
    args = a.parse_args()
    os.makedirs(args.out, exist_ok=True)
    env = {}
    if args.xor:
        start, length, value = args.xor
        data = bytearray(open(args.datafile or os.path.join(ROOT, 'tmp/f1ed/F1GP-Ed/2002.f1gp'), 'rb').read())
        for i in range(start, min(start + length, len(data))):
            data[i] ^= value
        args.datafile = os.path.join(args.out, args.name + '.datafile')
        open(args.datafile, 'wb').write(data)
    if args.datafile:
        env['DATAFILE'] = os.path.abspath(args.datafile)
    os.environ.setdefault('WARP', '1')
    s = f1_ed.server
    g = s.boot(env)
    try:
        g.stop()
        with Input(g) as c:
            c.fields(1500)      # Workbench boot and F1GP-Ed's windows
        if args.new:
            chord(g, R_AMIGA, KEY_N)
            chord(g, L_AMIGA, KEY_V)    # its confirmation, if one is shown
        chord(g, R_AMIGA, KEY_B)
        chord(g, L_AMIGA, KEY_V)        # "This will directly modify your F1GP binary"
        for _ in range(40):
            with Input(g) as c:
                c.fields(50)
            if not filecmp.cmp(PINNED, EDITED, shallow=False):
                break
        with Input(g) as c:
            c.fields(250)       # let the write finish
        s.handle(g, f'shot {os.path.join(os.path.abspath(args.out), args.name + ".png")}')
        shutil.copyfile(EDITED, os.path.join(args.out, args.name + '.f1gp'))
        same = filecmp.cmp(PINNED, EDITED, shallow=False)
        print(args.name, 'UNCHANGED' if same else 'saved')
    finally:
        s.handle(g, 'quit')


if __name__ == '__main__':
    main()
