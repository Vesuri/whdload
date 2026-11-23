#!/usr/bin/env python3
"""tools/aprof_report.py PROFILE [N]: an aprof profile (tools/vroom.py aprof) of the race: the
chip, gap and slave shares, then the N (default 25) call targets with the most inclusive time
(each target's outermost calls only), and the flat time by 4 KB block with its chip share.

A target above 24 bits is the slave (the profile maps it into the Zorro III window at
$40000000): on a 68020+ the race loop calls src/fixes.i's fix_Landscape at $C968, which jumps
to the landscape $E4F8, so the landscape's time is that target's."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'common/tools'))
import game_server  # noqa: F401,E402  (puts amigaxdev on the path)
from amigaxdev.aprof import parse_profile, call_tree  # noqa: E402

NAMES = {0xD13C: 'draw and swap', 0x10CD2: 'road spans', 0x140C0: 'objects',
         0x18154: 'scaler', 0x18330: 'scaler: an object', 0x1123A: 'blitter queue wait',
         0x10E72: 'span filler', 0x10C: 'slave WaitBlit0', 0x112: 'slave WaitBlit1',
         0x118: 'slave WaitBlit4', 0x11E: 'slave WaitBlit5', 0x124: 'slave WaitBlit6',
         0x13276: 'simulation', 0x12FA6: 'screen toggle'}


def main(argv):
    header, pcs, nodes = parse_profile(Path(argv[0]).read_text())
    top = int(argv[1]) if argv[1:] else 25
    _children, order, inclusive = call_tree(nodes)
    total = header['units']
    print(f"{header['vsyncs']} fields, cacr {header['cacr']:#x}: chip "
          f"{100 * header['chip_units'] / total:.1f}%, gap {100 * header['gap'] / total:.1f}%, "
          f"slave (above 24 bits) {100 * header.get('high', 0) / total:.1f}% of the time")
    agg = {}
    for n in order:
        if not n:
            continue
        target, a = nodes[n][1], nodes[n][0]
        while a and nodes[a][1] != target:
            a = nodes[a][0]
        d = agg.setdefault(target, [0, 0, 0])
        d[1] += nodes[n][4]
        d[2] += nodes[n][3]
        if not a:                      # outermost call of this target
            d[0] += inclusive[n]
    print('call targets (inclusive %, self %, calls):')
    for t, (i, c, s) in sorted(agg.items(), key=lambda kv: -kv[1][0])[:top]:
        name = NAMES.get(t, 'the slave' if t >= 0x1000000 else '')
        print(f'  ${t:08X} {100 * i / total:5.1f} {100 * s / total:5.1f} {c:6}  {name}')
    blocks = {}
    for pc, (u, _e, cu, _ca) in pcs.items():
        b = blocks.setdefault(pc & ~0xFFF, [0, 0])
        b[0] += u
        b[1] += cu
    print('flat, by 4 KB block (time %, chip share of it):')
    for b, (u, cu) in sorted(blocks.items(), key=lambda kv: -kv[1][0])[:16]:
        print(f'  ${b:05X} {100 * u / total:5.1f}  chip {100 * cu / max(u, 1):3.0f}%')


if __name__ == '__main__':
    main(sys.argv[1:])
