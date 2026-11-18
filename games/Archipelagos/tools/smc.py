#!/usr/bin/env python3
"""Self-modifying code check across the game's screens.

    python3 tools/smc.py OUT [ROUTE]

Needs a server just booted with tools/boot.sh on a CPU that records an instruction trace
(SETUP=a1200-030 EXTRA_ARGS=--uae_mmu_model=0, or the a500). Stops at the game's entry
(offset 0, `$201C`) and keeps the program image there as the reference: relocated and
patched by the slave, before the game runs. Then follows ROUTE (default 'end'; or 'death'),
tracing 2 fields at each stop, and compares the bytes of every instruction a trace executed
(from its PC up to the next executed PC, 10 bytes at most) with the reference. A
difference is code the game wrote after it started, or data the comparison ran into after
an rts or a jump. Also lists executed PCs outside the program image by 4 KB page (the
slave, WHDLoad and the ROM).

Routes (each from a fresh boot):
- end: the title, the archipelago screen, archipelago 1 created and in play, the map (F2),
  pan mode, both stones collapsed, the Obelisk destroyed, the end screen and its save, and
  space from there;
- death: archipelago 1, both stones collapsed, then 100 s for the Obelisk to destroy the
  player, the death screen, return (back to the archipelago screen), return again (select
  another archipelago) and space.

Writes OUT/report.txt (also printed). SPS 628 with VARIANT=ArchipelagosNTSC.
"""
import collections
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
import play  # noqa: E402
import route  # noqa: E402
from amigaxdev import barto  # noqa: E402

BODY = 0x201c
END = 0x166b8 if route.US else 0x16314       # the image's end (SPS 628, SPS 627)


class Check:
    def __init__(self, out):
        self.out = out
        self.ref = None
        self.lines = []
        self.outside = collections.Counter()
        self.total = 0

    def log(self, s):
        print(s, flush=True)
        self.lines.append(s)

    def reference(self):
        route.until(BODY)
        p = self.out / 'ref.bin'
        play.batch(f'dump binary memory {p} {BODY:#x} {END:#x}')
        self.ref = p.read_bytes()

    def trace(self, name, n=2):
        p = self.out / 'trace.bin'
        route.req('profile', str(n), str(p))
        t = barto.load(p)
        pcs, out = set(), collections.Counter()
        for f in t.fields:
            for pc, _, _ in t.instructions(f):
                if pc is None or pc == 0x7fffffff:
                    continue
                if BODY <= pc < END:
                    pcs.add(pc)
                else:
                    out[pc & ~0xfff] += 1
        self.outside.update(out)
        pcs = sorted(pcs)
        diff = []
        for i, pc in enumerate(pcs):
            end = min(pc + 10, pcs[i + 1] if i + 1 < len(pcs) else pc + 10)
            a, b = self.ref[pc - BODY:end - BODY], t.chip[pc:end]
            if a != b:
                diff.append(f'  ${pc - BODY:05X}  entry {a.hex()}  now {b.hex()}')
        self.total += len(diff)
        self.log(f'{name}: {len(pcs)} instructions executed in the image, {len(diff)} differ')
        for d in diff:
            self.log(d)
        p.unlink()


def end(c):
    route.until(route.TITLE_LOOP)
    c.trace('title')
    route.key('40', 5)
    route.until(route.ARCH_LOOP)
    c.trace('archipelago screen')
    route.key('40', 5)
    play.fields(20)
    c.trace('creating archipelago 1')
    route.until(route.GAME_LOOP)
    c.trace('in play')
    route.key('51', 4)                     # F2: the map
    play.fields(30)
    c.trace('map')
    route.key('40', 4)
    play.fields(30)
    route.run(['rmb 4'])
    play.mouse(4, 0, 20)
    c.trace('pan mode')
    route.run(['rmb 4', 'f 20'])
    clicked = play.click

    def click():
        clicked()
        play.fields(6)
        c.trace(f'after a click ({play.var(play.LEFT)} stones left)', 4)
    play.click = click
    play.stones(log=lambda s: None)
    play.obelisk(log=lambda s: None)
    play.click = clicked
    for i in range(6):
        play.fields(100)
        c.trace(f'after the Obelisk, field {100 * (i + 1)}')
    route.key('40', 5)
    play.fields(50)
    c.trace('space after the end')
    play.fields(200)
    c.trace('200 fields later')


def death(c):
    route.run(['title', 'arch', 'play'])
    play.stones(log=lambda s: None)
    c.trace('stones collapsed')
    for i in range(10):
        play.fields(500)
    c.trace('after 100 s')
    play.fields(300)
    c.trace('death, 6 s later')
    route.key('44', 5)                     # return: retry
    play.fields(100)
    c.trace('return')
    play.fields(300)
    c.trace('300 fields later')
    route.until(route.ARCH_LOOP)
    route.key('44', 5)                     # return: select another archipelago
    play.fields(100)
    c.trace('selecting another archipelago')
    route.key('40', 5)
    play.fields(300)
    c.trace('space, 300 fields later')


def main(args):
    if not args:
        sys.exit(__doc__)
    out = Path(args[0]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    name = args[1] if len(args) > 1 else 'end'
    c = Check(out)
    route.req('stop')
    c.reference()
    {'end': end, 'death': death}[name](c)
    c.log(f'{c.total} differences')
    c.log('executed outside the image (4 KB pages): ' + ', '.join(
        f'${p:06X} {n}' for p, n in sorted(c.outside.items())))
    (out / 'report.txt').write_text('\n'.join(c.lines) + '\n')


if __name__ == '__main__':
    main(sys.argv[1:])
