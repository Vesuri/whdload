#!/usr/bin/env python3
"""The panning benchmark: archipelago 1 from its first interactive field, the right mouse
button to enter pan mode, then the mouse moving right for PAN fields, all traced.

    python3 tools/bench.py OUT [PAN [DX]]

Needs a server just booted with tools/boot.sh, on a CPU that records an instruction trace
(68000, 68020, or the 68030 without its MMU model: SETUP=a1200-030
EXTRA_ARGS=--uae_mmu_model=0; WHDLoad does not use the 68030's MMU without its MMU option,
so the game runs the same). Runs tools/route.py's 'start', then traces back to back in
1-field chunks: the button held 4 fields and released for 4, then PAN fields (default 250,
5 s PAL) with the mouse moved DX counts right before each (default 4: the heading turns 4 of
its 720 units, 2 degrees, a field). Each chunk is reduced (tools/reduction.py, with tools/report.py's
marks) and deleted. Writes OUT/profile.pkl.gz, OUT/state.tsv (per traced field, from
the chip snapshot at the field's start: the game's field counter, the heading, the world
tick countdown, the back buffer), OUT/chip.bin (chip memory at the start of the last field,
for disassembly), OUT/end.png, then OUT/report.txt (tools/report.py).
"""
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
import route  # noqa: E402
import report  # noqa: E402
from amigaxdev import barto  # noqa: E402
from reduction import GameReduction  # noqa: E402

STATE = [  # (name, SPS 627 body offset, size): read after each traced field
    ('fields', 0x12862, 4),   # the game's field counter (the level 3 handler; 0 at play start)
    ('heading', 0x12880, 2),  # 0..719, half degrees
    ('tick', 0x129b6, 2),     # the world tick countdown: the VBL decrements it, a tick is due
                              # below 0 and reloads it from $149d0 (5)
    ('back', 0x1286a, 4),     # the buffer being drawn ($5c780 or $663c0)
]


def sample():
    out = []
    for _, a, n in STATE:
        v = int.from_bytes(route.peek(route.addr(a), n), 'big')
        out.append(v - (1 << 16) if n == 2 and v & 0x8000 and _ == 'tick' else v)
    return out


def main(args):
    if not args:
        sys.exit(__doc__)
    out = Path(args[0]).resolve()
    pan = int(args[1]) if len(args) > 1 else 250
    dx = int(args[2]) if len(args) > 2 else 4
    out.mkdir(parents=True, exist_ok=True)
    route.run(['start'])
    b = route.body()
    marks = dict(report.MARKS)
    j = route.peek(route.addr(0x11efa), 6)
    if j[:2] == b'\x4e\xf9':           # 68020+: the slave's wait, which runs the blit queue
        bw = int.from_bytes(j[2:], 'big')
        marks['bw_in'] = bw
        marks['bw_out'] = bw + route.peek(bw, 0x80).index(b'\x4a\x40\x4e\x75') + 2
    red = GameReduction(marks=marks, tally=report.VBL_SPIN,
                        remap=(b, b + 0x15000, b - route.CHIP_BODY) if route.fast() else None)
    chunk = out / 'chunk.bin'
    states = []

    def trace(n_fields=1):
        nonlocal last
        route.req('profile', str(n_fields), str(chunk))
        t = red.feed(chunk)
        states.append(sample())
        last = t
        chunk.unlink()

    last = None
    route.req('gdb', 'monitor input JOY1_2ND_BUTTON 1')
    for _ in range(4):
        trace()
    route.req('gdb', 'monitor input JOY1_2ND_BUTTON 0')
    for _ in range(4):
        trace()
    for i in range(pan):
        route.req('gdb', f'monitor mouse {dx} 0')
        trace()
    (out / 'chip.bin').write_bytes(last.chip)
    shot = last.fields[-1].shot
    if shot:
        (out / 'end.png').write_bytes(shot)
    red.save(out / 'profile.pkl.gz')
    with open(out / 'state.tsv', 'w') as f:
        f.write('\t'.join(n for n, _, _ in STATE) + '\n')
        for s in states:
            f.write('\t'.join(str(v) for v in s) + '\n')
    text = report.report(red, states, dict(pan=pan, dx=dx))
    (out / 'report.txt').write_text(text)
    print(text)


if __name__ == '__main__':
    main(sys.argv[1:])
