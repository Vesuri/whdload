#!/usr/bin/env python3
"""Self-modifying code check: executed code that differs from the relocated program file.

    python3 tools/smc.py RUN [PROGRAM]

RUN is a tools/bench.py output (profile.pkl.gz: the executed PCs; chip.bin: chip memory at
the start of its last traced field). PROGRAM (default tmp/game/Archipelagos/data/
Archipelagos_03FC00, SPS 627) is relocated to $201C as the slave does, then the bytes from
each executed PC up to the next executed PC (10 at most) are compared with chip.bin. A
difference is a slave patch (docs/internals.md lists them), data the comparison ran into
after an rts, or code the game wrote. Prints program offsets.
"""
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
from reduction import GameReduction  # noqa: E402

BODY = 0x201c


def relocate(prog):
    """The ST program's text and data relocated to BODY."""
    tlen, dlen, _, slen = struct.unpack_from('>IIII', prog, 2)
    img = bytearray(prog[0x1c:0x1c + tlen + dlen])
    rel = 0x1c + tlen + dlen + slen
    off = struct.unpack_from('>I', prog, rel)[0]
    p = rel + 4
    if off:
        while True:
            v = struct.unpack_from('>I', img, off)[0]
            struct.pack_into('>I', img, off, (v + BODY) & 0xffffffff)
            b = prog[p]
            p += 1
            if b == 0:
                break
            while b == 1:
                off += 254
                b = prog[p]
                p += 1
            off += b
    return img


def main(args):
    if not args:
        sys.exit(__doc__)
    run = Path(args[0])
    prog = Path(args[1]) if len(args) > 1 else ROOT / 'tmp/game/Archipelagos/data/Archipelagos_03FC00'
    img = relocate(prog.read_bytes())
    chip = (run / 'chip.bin').read_bytes()
    r = GameReduction.load(run / 'profile.pkl.gz')
    pcs = sorted(pc for pc in r.counts if BODY <= pc < BODY + len(img))
    n = 0
    for i, pc in enumerate(pcs):
        end = min(pc + 10, pcs[i + 1] if i + 1 < len(pcs) else pc + 10)
        a, b = bytes(img[pc - BODY:end - BODY]), chip[pc:end]
        if a != b:
            n += 1
            print(f'${pc - BODY:05X}  file {a.hex()}  run {b.hex()}')
    print(f'{len(pcs)} executed instructions in the program, {n} differ')


if __name__ == '__main__':
    main(sys.argv[1:])
