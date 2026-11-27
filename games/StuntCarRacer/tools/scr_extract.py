#!/usr/bin/env python3
"""Extract the decrypted main program from a Stunt Car Racer / Stunt Track Racer Disk.1.

    python3 tools/scr_extract.py DISK OUT [--ntsc]

The main program is at disk offset $dc00 and runs at $e700. On the original disks it starts
with `bra` ($6000007a) and the Rob Northen encrypted body begins at +$c98; the slave's
_Decrypt removes it with three keys and the program is the decrypted longwords from +$c9c
(docs/internals.md). A cracked disk (Quartex) has the plain program at $dc00. OUT gets the
program as it lies at $e700: $18ef8 longwords (PAL), or what the image holds (NTSC).
"""
import argparse
import struct
import sys

M = 0xffffffff


def decrypt(words, d5, d6, d7, step_first=True):
    """The slaves' Rob Northen loop: for each longword, shift the key, adjust it by the two
    key bits, add it to the data and the data to it."""
    b5, b6 = d5 & 31, d6 & 31
    out = []
    for i, w in enumerate(words):
        if step_first or i:
            d7 = (d7 << 1) & M
            if bool(d7 >> b5 & 1) != bool(d7 >> b6 & 1):
                d7 = (d7 + 1) & M
        w = (w + d7) & M
        out.append(w)
        d7 = (d7 + w) & M
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('disk')
    p.add_argument('out')
    p.add_argument('--ntsc', action='store_true', help='Stunt Track Racer')
    a = p.parse_args()
    disk = open(a.disk, 'rb').read()
    base = 0xdc00
    if a.ntsc:
        # StuntTrackRacer.s _PatchMain: longwords decrypted from +$c9c and moved down, keys
        # 17, 7, $207c0000 less the first encrypted longword, no shift first. Its count
        # ($19e40) runs past the end of the image; the program is what the image holds.
        n = (len(disk) - base - 0xc9c) // 4
        enc = list(struct.unpack('>%dL' % n, disk[base + 0xc9c:base + 0xc9c + 4 * n]))
        d7 = (0x207c0000 - enc[0]) & M
        prog = decrypt(enc, 17, 7, d7, step_first=False)
    else:
        n = 0x18ef8
        if struct.unpack('>L', disk[base:base + 4])[0] == 0x6000007a:
            enc = list(struct.unpack('>%dL' % (n + 1), disk[base + 0xc98:base + 0xc98 + 4 * (n + 1)]))
            prog = decrypt(enc, 0xc905b365, 0xa0cff27b, 0x59f3a592)[1:]
        else:
            prog = list(struct.unpack('>%dL' % n, disk[base:base + 4 * n]))
    open(a.out, 'wb').write(struct.pack('>%dL' % len(prog), *prog))
    print('%s: %d bytes, first longword $%08x' % (a.out, 4 * len(prog), prog[0]))


if __name__ == '__main__':
    sys.exit(main())
