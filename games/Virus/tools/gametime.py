#!/usr/bin/env python3
"""Is game time tied to frames? The work memory at a demo frame, compared across machines.

    python3 tools/gametime.py capture OUT [FRAME]   from a server booted with tools/boot.sh
    python3 tools/gametime.py compare A B

`capture` runs to the demo's start, steps 5 fields at a time to FRAME-10 (default 200; it
prints the fields that took), then stops at the main loop's top ($64204) with the frame
counter $c9f4 at FRAME (a conditional breakpoint, outside any measurement) and dumps
$1000-$3b7ff (OUT) and the Disk.1 image $3b800-$687ff (OUT.img), from where they run
(tools/codebase.py). `compare` lists the bytes that differ.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parents[1] / 'common/tools'))


def capture(out, frame):
    from game_server import game_server
    srv = game_server('virus')
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    sys.path.insert(0, str(ROOT / 'tools'))
    import codebase
    d = codebase.delta(srv)
    fc = codebase.at(0xc9f4, d)

    def counter():
        return int(next(w for w in srv.request(f'peek {fc:x} 2').split() if len(w) == 4), 16)

    srv.request(f'until {0x641fe + d:#x}')
    n = 0
    while counter() < frame - 10:
        srv.request('fields 5')
        n += 5
    print(f'frame {counter()} after {n} fields')
    srv.request(f'gdb break *{0x64204 + d:#x} if *(unsigned short *){fc:#x} == {frame}')
    srv.request('gdb continue')
    srv.request('gdb delete')
    # $1000-$687ff as the game sees it: from where it was moved to, the chip data from chip
    lo, hi = codebase.MOVED
    srv.request(f'gdb dump binary memory {out}.all {lo + d:#x} {hi + d:#x}')
    srv.request(f'gdb dump binary memory {out}.chip {codebase.CHIP[0]:#x} {codebase.CHIP[1]:#x}')
    whole = bytearray(Path(f'{out}.all').read_bytes())
    whole[codebase.CHIP[0] - lo:codebase.CHIP[1] - lo] = Path(f'{out}.chip').read_bytes()
    Path(out).write_bytes(whole[:0x3b800 - lo])
    Path(f'{out}.img').write_bytes(whole[0x3b800 - lo:])
    Path(f'{out}.all').unlink()
    Path(f'{out}.chip').unlink()
    print(f'stopped at frame {counter()}')


def runs(a, b, base):
    out, i = [], 0
    while i < len(a):
        if a[i] != b[i]:
            j = i
            while j < len(a) and a[j] != b[j]:
                j += 1
            out.append((base + i, j - i))
            i = j
        else:
            i += 1
    return out


def compare(a, b):
    for suffix, base, name in (('', 0x1000, 'work memory $1000-$3b7ff'),
                               ('.img', 0x3b800, 'Disk.1 image $3b800-$687ff')):
        r = runs(Path(a + suffix).read_bytes(), Path(b + suffix).read_bytes(), base)
        print(f'{name}: {sum(n for _, n in r)} bytes differ in {len(r)} runs '
              + ' '.join(f'${s:05x}+{n}' for s, n in r[:20]))


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == 'capture':
        capture(a[1], int(a[2]) if len(a) > 2 else 200)
    elif len(a) == 3 and a[0] == 'compare':
        compare(a[1], a[2])
    else:
        sys.exit(__doc__)
