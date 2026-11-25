#!/usr/bin/env python3
"""Differential check of the slave's unpacker (_lzw) against the game's (golf hunk 23).

    python3 tools/lzwcheck.py [LIMITS]

Loads tmp/game/Links/data/golf's hunks as tools/drawcheck.py does and the slave's _lzw and
_lzwinit (assembled from src/Links_WHD.s), with a dos Read that serves a file from memory.
For every packed member of every file in tmp/game/*/data and data/courses (a 122-byte
"MDmd" header, byte 5 set), it unpacks the member with hunk 23 $1e0 twice, as hunk 13 sets
it up (the input and dictionary in the buffer _lzwbuf gives): once with the game's $0 and
once (on a second machine) with $0 jumping to _lzw. Then it compares the registers $1e0 leaves, hunk 23's
variables ($340-$39b), the output buffer (to 64 KB past the end), the input and dictionary,
and the 32 KB under the dictionary. LIMITS (default 2) more runs of each member set hunk
23 $397 and a random count in $35c (hunk 31 $1032 loads part of a file that way).
"""
import hashlib
import random
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawcheck import (HUNKS, REG_A0, REG_D0, SENTINEL, STACK, Machine,  # noqa: E402
                       hunks, load_unicorn)

ROOT = Path(__file__).resolve().parents[1]
CODE_NEW = 0x600000
FILE, FILE_MAX = 0x460000, 0xA0000      # the member and what follows it in its file
GUARD = 0x510000                        # 64 KB under LZWBUF
LZWBUF = 0x520000                       # 64 KB: input, dictionary, lengths
OUT = 0x540000                          # the output, then 64 KB checked for stray writes
DOS = 0x5F0000                          # a dos base: -42 jumps to the test's Read
H0, H23 = HUNKS, HUNKS + 0x10000 * 23


def assemble():
    """_lzw at CODE_NEW, _lzwinit at +4; then the addresses of LZWBUF, _read, FPOS, FEND."""
    src = (ROOT / 'src/Links_WHD.s').read_text(encoding='latin-1')
    start = src.index("; The game's files are LZW-packed")
    end = src.index('\tMC68000\n', src.index('\n_lzw\t')) + 9
    text = (f'\tORG\t${CODE_NEW:x}\n\tbra.w\t_lzw\n\tbra.w\t_lzwinit\n'
            f'\tdc.l\tLZWBUF,_read,FPOS,FEND\n'
            '_read\tmove.l\tFEND(pc),d0\n\tsub.l\tFPOS(pc),d0\n\tcmp.l\td3,d0\n'
            '\tbls.b\t.n\n\tmove.l\td3,d0\n.n\tmove.l\tFPOS(pc),a0\n\tmove.l\td2,a1\n'
            '\tmove.l\td0,d1\n\tbeq.b\t.e\n.c\tmove.b\t(a0)+,(a1)+\n\tsubq.l\t#1,d1\n'
            '\tbne.b\t.c\n.e\tlea\tFPOS(pc),a1\n\tadd.l\td0,(a1)\n\trts\n'
            'FPOS\tdc.l\t0\nFEND\tdc.l\t0\nLZWBUF\tdc.l\t0\n'
            f'{src[start:end]}\n')
    (ROOT / 'tmp').mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(dir=ROOT / 'tmp'))
    s, b = tmp / 'lzw.s', tmp / 'lzw.bin'
    s.write_text(text, encoding='latin-1')
    try:
        subprocess.run(['vasmm68k_mot', '-m68020', '-devpac', '-Fbin', '-quiet', '-o', str(b),
                        str(s)], check=True)
        data = b.read_bytes()
    finally:
        for p in tmp.iterdir():
            p.unlink()
        tmp.rmdir()
    return data, struct.unpack_from('>4I', data, 8)


def members():
    """(name, file bytes from the member's header on) for each distinct packed member."""
    seen, out = set(), []
    files = sorted(p for d in (ROOT / 'tmp/game').glob('*/data')
                   for p in list(d.iterdir()) + list((d / 'courses').glob('*')) if p.is_file())
    for f in files:
        d = f.read_bytes()
        i = d.find(b'MDmd')
        while i >= 0:
            n = d[i + 40]
            size, packed = struct.unpack_from('>II', d, i + 24)
            if d[i + 5] == 1 and 0 < n < 40 and size and packed:
                key = hashlib.sha256(d[i:i + 122 + packed]).digest()
                if key not in seen:
                    seen.add(key)
                    name = f'{f.name}:{d[i + 41:i + 41 + n].decode("latin-1")}'
                    out.append((name, d[i:i + 122 + min(FILE_MAX - 122, len(d) - i - 122)],
                                size))
            i = d.find(b'MDmd', i + 1)
    return out


def run(m, hs, addrs, member, size, limit, seed):
    lzwbuf, read, fpos, fend = addrs
    rng = random.Random(seed)
    m.write(H23 + 0x340, hs[23][0x340:])                            # the variables
    m.write(lzwbuf, LZWBUF.to_bytes(4, 'big'))
    m.write(GUARD, bytes(rng.randrange(256) for _ in range(0x10000)))
    m.write(LZWBUF, bytes(rng.randrange(256) for _ in range(0xC000)) + bytes(0x4000))
    m.call(CODE_NEW + 4, [0] * 8 + [LZWBUF] + [0] * 6)             # _lzwinit
    m.write(OUT, bytes([0xA5]) * (size + 0x10000))
    m.write(FILE, member[122:])
    m.write(fpos, FILE.to_bytes(4, 'big'))
    m.write(fend, (FILE + len(member) - 122).to_bytes(4, 'big'))
    m.write(DOS - 42, b'\x4e\xf9' + read.to_bytes(4, 'big'))
    m.write(H0 + 0x168, DOS.to_bytes(4, 'big'))
    w = lambda o, v, n: m.write(H23 + o, v.to_bytes(n, 'big'))      # as hunk 13 $264-$2f8
    w(0x340, 0x1234, 4)
    w(0x38a, 13, 2)
    w(0x388, 0x4000, 2)
    w(0x350, LZWBUF, 4)
    w(0x348, LZWBUF + 0x4000, 4)
    w(0x354, OUT, 4)
    w(0x397, 1 if limit is not None else 0, 1)
    w(0x35c, limit or 0, 4)
    regs = [rng.randrange(1 << 32) for _ in range(15)]
    r = m.call(H23 + 0x1E0, regs)
    keep = [r[i] for i in (2, 6, 7)] + [r[8 + i] for i in (2, 3, 4, 5, 6, 7)]
    count = struct.unpack('>I', m.read(H23 + 0x34C, 4))[0]
    return (keep, m.read(H23 + 0x340, 0x5C), m.read(OUT, size + 0x10000),
            m.read(LZWBUF, 0xC000), m.read(GUARD, 0x10000), count)


def main():
    limits = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    hs = hunks(ROOT / 'tmp/game/Links/data/golf')
    code, addrs = assemble()
    uc = load_unicorn()
    game, new = Machine(uc), Machine(uc)
    # Two machines: Unicorn keeps code it has translated when memory is written, so a
    # patch cannot be put in and taken out between runs.
    for m in game, new:
        for i, h in enumerate(hs):
            m.write(HUNKS + 0x10000 * i, h)
        m.write(CODE_NEW, code)
    new.write(H23, b'\x4e\xf9' + CODE_NEW.to_bytes(4, 'big'))        # PL_P $0,_lzw
    names = ('registers', 'variables', 'output', 'input and dictionary', 'under it', 'count')
    rng = random.Random(1)
    runs = bad = 0
    for k, (name, member, size) in enumerate(members()):
        for limit in [None] + [rng.randrange(size + 16) for _ in range(limits)]:
            a = run(game, hs, addrs, member, size, limit, k)
            b = run(new, hs, addrs, member, size, limit, k)
            runs += 1
            if limit is None and a[5] != size:
                print(f'{name}: the game unpacked {a[5]} bytes, the header says {size}')
            if a != b:
                bad += 1
                diff = [names[i] for i in range(6) if a[i] != b[i]]
                print(f'{name} limit {limit}: differs in {", ".join(diff)}')
    print(f'{runs - bad}/{runs} equal ({len(members())} members, {limits} limits each)')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
