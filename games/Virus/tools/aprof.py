#!/usr/bin/env python3
"""Exact cycles and chip-access time per routine group over the demo window (aprof).

    python3 tools/aprof.py run OUT.aprof [FIELDS]    from a server booted with
        FSUAE=$FSUAE_APROF SETUP=a1200-030 EXTRA_ARGS=--uae_mmu_model=0 WHD_ARGS=CACHE tools/boot.sh
    python3 tools/aprof.py report OUT.aprof

`run` goes to the demo's start, profiles FIELDS fields (default 1250, as tools/bench.py)
and reads the frame counter. `report` groups every PC's units and chip units (cycles spent
on chip-bus accesses, waits included) and prints the CACR the profile recorded.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
sys.path.insert(0, str(ROOT.parents[1] / 'common/tools'))
from amigaxdev.aprof import parse_profile  # noqa: E402

SPIN = {0x6547e, 0x65484}


def group(pc):
    if pc in SPIN:
        return 'busy-wait for the clear ($6547e)'
    if 0x200000 <= pc < 0xf80000:
        return 'WHDLoad (fast memory)'
    if 0x67d8e <= pc < 0x68400:
        return 'polygon fill edge stepping ($67d8e)'
    if 0x57000 <= pc < 0x60000 and not 0x58000 <= pc < 0x59000:
        return 'span writers and other $57000-$5ffff'
    if 0x60a1c <= pc < 0x60c40:
        return 'particles ($60a1c)'
    if 0x65174 <= pc < 0x65600:
        return 'renderer own code ($65174)'
    if 0x67300 <= pc < 0x67d8e:
        return 'objects ($67300-$67d8d)'
    return 'other game code'


def report(path):
    h, pcs, _ = parse_profile(Path(path).read_text())
    units = h['units']
    g = {}
    for pc, (u, _n, cu, ca) in pcs.items():
        a = g.setdefault(group(pc), [0, 0, 0])
        a[0] += u
        a[1] += cu
        a[2] += ca
    print(f'{h["vsyncs"]} vsyncs, {h["cpu_model"]}, CACR ${h["cacr"]:04x}; chip access '
          f'{100 * h["chip_units"] / units:.1f}% of all time ({h["chip_accesses"]} accesses)')
    print(f'  {"group":40} {"time":>7} {"chip share of it":>17}')
    for k, (u, cu, _ca) in sorted(g.items(), key=lambda x: -x[1][0]):
        print(f'  {k:40} {100 * u / units:6.2f}% {100 * cu / u:16.1f}%')
    rest = [v for k, v in g.items() if not k.startswith('busy')]
    print(f'  all but the busy-wait: {100 * sum(v[1] for v in rest) / sum(v[0] for v in rest):.1f}% chip access')


def run(path, fields):
    from game_server import game_server
    srv = game_server('virus')
    srv.request('until 0x641fe')
    srv.request('gdb monitor aprof start')
    srv.request(f'fields {fields}')
    srv.request(f'gdb monitor aprof stop {Path(path).resolve()}')
    print('frame counter', srv.request('peek c9f4 2').split()[0])
    report(path)


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == 'run':
        run(a[1], int(a[2]) if len(a) > 2 else 1250)
    elif len(a) == 2 and a[0] == 'report':
        report(a[1])
    else:
        sys.exit(__doc__)
