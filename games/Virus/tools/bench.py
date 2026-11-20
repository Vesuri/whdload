#!/usr/bin/env python3
"""The demo benchmark: the game's own DEMO mode from its first field, all traced.

    python3 tools/bench.py OUT [FIELDS [CHUNK]]

Needs a server just booted with tools/boot.sh on a CPU that records an instruction trace
(68000, 68020, or the 68030 without its MMU model), for example

    SETUP=a1200-030 EXTRA_ARGS=--uae_mmu_model=0 WHD_ARGS=CACHE tools/boot.sh

From the boot it runs to the demo's start (Disk.1 offset $289fe, $641fe: the last call
before the main loop, once per game or demo start; the title and the attract screen take
about 990 fields before it), then traces FIELDS fields (default 1250, 25 s PAL) back to
back in CHUNK-field files (default 25), each reduced (amigaxdev.callprofile) and deleted.
After each chunk it reads the game's frame counter ($c9f4, incremented at the main loop's
top, cleared at the start). Writes OUT/profile.pkl.gz, OUT/frames.tsv (the counter after
each chunk), OUT/end.png (the last field) and OUT/report.txt (tools/report.py).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
import report  # noqa: E402
from reduction import GameReduction  # noqa: E402

sys.path.insert(0, str(ROOT.parents[1] / 'common/tools'))
from game_server import game_server  # noqa: E402

DEMO_START = 0x641fe
FRAME_COUNTER = 0xc9f4


def main(args):
    if not args:
        sys.exit(__doc__)
    out = Path(args[0]).resolve()
    total = int(args[1]) if len(args) > 1 else 1250
    size = int(args[2]) if len(args) > 2 else 25
    out.mkdir(parents=True, exist_ok=True)
    srv = game_server('virus')

    def req(*words):
        return srv.request(' '.join(words))

    def counter():
        txt = req('peek', f'{FRAME_COUNTER:x}', '2')
        return int(next(w for w in txt.split() if len(w) == 4), 16)

    print(req('until', hex(DEMO_START)).strip().splitlines()[-1])
    red = GameReduction(marks=report.MARKS, tally=report.SPIN)
    chunk = out / 'chunk.bin'
    rows = [(0, counter())]
    done, last = 0, None
    while done < total:
        n = min(size, total - done)
        reply = req('profile', str(n), str(chunk))
        if not chunk.exists():
            sys.exit(f'profile failed: {reply}')
        last = red.feed(chunk)
        chunk.unlink()
        done += n
        rows.append((done, counter()))
        print(f'{done}/{total} fields, frame counter {rows[-1][1]}', flush=True)
    shot = last.fields[-1].shot
    if shot:
        (out / 'end.png').write_bytes(shot)
    red.save(out / 'profile.pkl.gz')
    with open(out / 'frames.tsv', 'w') as f:
        f.write('fields\tframe_counter\n')
        f.writelines(f'{a}\t{b}\n' for a, b in rows)
    text = report.report(red, rows)
    (out / 'report.txt').write_text(text)
    print(text)


if __name__ == '__main__':
    main(sys.argv[1:])
