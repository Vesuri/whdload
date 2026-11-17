#!/usr/bin/env python3
"""Execute the release slave's player-bolt near plane at the projection's two sites.

The projection (CD32 E:2a086, OCS O:290fa) culls a slot until it is past
256 times the near-plane word, the radius of the ship the view belongs to.
src/near_plane.s replaces the word's load at both near tests: in the forward
view, outside the intro, the player's own cannon bolts (class 8, shooter
slot 0) take at most the Hornet's 100. Each site's patched 6 bytes run from
a trampoline in the game's memory with the slave loaded, for the player's
bolt, other classes and shooters, other views, the intro and planes at or
below 100; d0 must be the expected plane, zero-extended, with every other
register kept. The same sites with the native bytes are the control: a player
bolt must keep the ship's plane there. CD32 runs English and German on the
68020 and 68040 models, OCS on the 68000 and 68020 models.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from field_objects_check import machine
from ocs_display_check import Native, CODE, DATA, word, long
from ocs_clock_check import SLAVE, machine as ocs_machine
from ocs_reconstruct import ROOT, new_output, require
from variants import get

TRAMPOLINE = 0x3f0000          # scratch: the site's 6 bytes, then rts
SITES = {'cd32': (0x2a166, 0x2a1b0), 'ocs': (0x291da, 0x29224)}
# A4 offsets: near plane, class words, shooter bytes, view word.
A4 = {'cd32': (7030, 5888, 14954, -18280), 'ocs': (4868, 3726, 12376, -18318)}
SENTINEL = {r: 0x5a000000+r*0x111 for r in range(1, 17) if r not in (5, 8, 9)}


def cases():
    # (name, near, class, shooter, view, intro, expected)
    yield 'player bolt', 180, 8, 0, 0, 0, 100
    yield 'player bolt, large ship', 400, 8, 0, 0, 0, 100
    yield 'player bolt, plane 100', 100, 8, 0, 0, 0, 100
    yield 'player bolt, plane 60', 60, 8, 0, 0, 0, 60
    yield 'player bolt, plane 10', 10, 8, 0, 0, 0, 10
    yield 'enemy bolt', 180, 8, 3, 0, 0, 180
    yield 'enemy bolt, shooter 9', 180, 8, 9, 0, 0, 180
    yield 'ship', 180, 12, 0, 0, 0, 180
    yield 'missile', 180, 11, 0, 0, 0, 180
    yield 'effect', 180, 5, 0, 0, 0, 180
    yield 'left view', 180, 8, 0, 1, 0, 180
    yield 'external view', 180, 8, 0, 8, 0, 180
    yield 'intro', 180, 8, 0, 0, 1, 180


def exercise(c, a4n, intro, sites, slot=13, control=False):
    near, cls, owner, view = a4n
    base = DATA+0x7ffe
    results = []
    for site in sites:
        patch = c.read(CODE+site, 6)
        c.write(TRAMPOLINE, patch+word(0x4e75))
        for name, plane, k, shooter, v, i, expected in cases():
            if control:
                expected = plane
            c.write(base+near, word(plane))
            c.write(base+cls+2*slot, word(k))
            c.write(base+owner+slot, bytes((shooter,)))
            c.write(base+view, word(v & 0xffff))
            c.write(intro, word(i))
            regs = dict(SENTINEL); regs[11] = slot; regs[9] = 0xdeadbeef
            c.run(TRAMPOLINE-CODE, registers=regs)
            got = c.reg(9)
            require(got == expected, f'{site:x} {name}: plane {got} expected {expected}')
            for r, value in regs.items():
                if r != 9:
                    require(c.reg(r) == value, f'{site:x} {name}: register {r} changed')
            require(c.reg(8) == 0x1f0000+4, f'{site:x} {name}: stack balance')
            results.append(name)
    return len(results)


def run_cd32(build, model, german):
    c, sy = machine(build, 'cd32', model, german)
    try:
        if german:
            import german_map
            m = german_map.get()
            at, a4 = m.code, m.a4
        else:
            at, a4 = (lambda e: e), (lambda n: n)
        sites = [at(s) for s in SITES['cd32']]
        a4n = tuple(a4(n) for n in A4['cd32'])
        intro = SLAVE+sy['intro_active']
        native = {s: c.read(CODE+s, 6) for s in sites}
        for s in sites:
            require(native[s][:4] == b'\x70\x00\x30\x2c', f'native site {s:x}')
        n = exercise(c, a4n, intro, sites, control=True)
        for s in sites:   # the slave's timing_install writes jsr near_plane here
            c.write(CODE+s, struct.pack('>HI', 0x4eb9, SLAVE+sy['near_plane']))
        return n, exercise(c, a4n, intro, sites)
    finally:
        c.close()


def run_ocs(build, model):
    game = ROOT/'tmp/game/WingCommander/data/Wing.english'
    bare = Native(game, model=model)
    c, sy = ocs_machine(build, model)
    try:
        sites = SITES['ocs']
        meta = json.loads((build/'build.json').read_text())
        require(sum(1 for off, label, _ in meta['hooks'] if label == 'near_plane' and off in sites) == 2, 'OCS hook sites')
        for s in sites:
            require(c.read(CODE+s, 6) == struct.pack('>HI', 0x4eb9, SLAVE+sy['near_plane']), f'OCS hook at {s:x}')
            require(bare.read(CODE+s, 4) == b'\x70\x00\x30\x2c', f'OCS native site {s:x}')
        intro = SLAVE+sy['intro_active']
        hooked = exercise(c, A4['ocs'], intro, sites)
        for s in sites:
            c.write(CODE+s, bare.read(CODE+s, 6))
        return exercise(c, A4['ocs'], intro, sites, control=True), hooked
    finally:
        c.close(); bare.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path)
    p.add_argument('--variant', choices=('cd32', 'ocs'), default='cd32')
    p.add_argument('--german', action='store_true')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    out = new_output(a.output); out.mkdir(parents=True)
    report = {}
    if a.variant == 'ocs':
        for model in (1, 2):
            control, hooked = run_ocs(a.build, model)
            report[f'680{model-1}0' if model == 1 else '68020'] = dict(control=control, hooked=hooked)
        slave = a.build/'WingCommander.Slave'
    else:
        for model in (2, 4):
            control, hooked = run_cd32(a.build, model, a.german)
            report[f'680{model}0'] = dict(control=control, hooked=hooked)
        slave = a.build/'WingCommanderCD32.Slave'
    out.joinpath('report.json').write_text(json.dumps(dict(
        passed=True, variant=a.variant, german=a.german, models=report,
        slave_sha256=hashlib.sha256(slave.read_bytes()).hexdigest()), indent=2)+'\n')
    print(a.variant+(' German' if a.german else ''), 'near plane:',
          sum(v['hooked'] for v in report.values()), 'hooked and',
          sum(v['control'] for v in report.values()), 'control cases pass')


if __name__ == '__main__':
    main()
