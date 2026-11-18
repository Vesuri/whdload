#!/usr/bin/env python3
"""Summarise profile_flight.py's aprof window: aprof_report.py OUT [TOP]

For each segment (OUT/f5.prof, OUT/f6.prof): the frame rate (gs2.run's present, code $129c4,
once per frame), the CACR, the chip-bus share, the time by kind (frame-cap spin, blitter-wait
loops, stack and call instructions, the rest of gs2.run, outside gs2.run) and the TOP routines of
gs2.run by self time (a routine is the code from one call target to the next; aprof's call tree
is not used, its returns are unpaired). Shares are of all emulated time in the segment, chip-bus
shares of the same total. Also written to OUT/report.txt.
"""
import bisect
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _amigaxdev  # noqa: F401,E402
from amigaxdev import aprof  # noqa: E402
from amigaxdev.env import tool  # noqa: E402
import gs2  # noqa: E402

PRESENT = 0x129c4                  # rotates the three screens, writes COP1LC: once per frame
CAP_SPIN = {0x2c6, 0x2cc, 0x2d0}   # main loop: wait until 6 ticks of 64 Hz since the frame began
VBL_WAIT = {0x129aa, 0x129b0}      # wait for the next VBL (the VBL client sets a flag)


def listing(out):
    """{offset: instruction} for gs2.run's code hunk (objdump of the installed file)."""
    hs, rel = gs2.hunks()
    path = out / 'gs2-code.bin'
    path.write_bytes(hs[0][1])
    text = subprocess.run([tool('objdump'), '-D', '-b', 'binary', '-m', 'm68k:68020', str(path)],
                          capture_output=True, text=True, check=True).stdout
    path.unlink()
    ins = {}
    for line in text.splitlines():
        m = re.match(r'\s*([0-9a-f]+):\s+(?:[0-9a-f]{4} )+\s*(.*)', line)
        if m:
            ins[int(m.group(1), 16)] = m.group(2)
    return ins, rel.get(0, {})


def routines(ins, rel, targets):
    """Routine starts: bsr targets, jsr targets into the code hunk, traced call targets."""
    starts = {0} | set(targets)
    for o, t in ins.items():
        m = re.match(r'(bsr\.[bswl]|jsr) 0x([0-9a-f]+)$', t)
        if m and (m.group(1) != 'jsr' or rel.get(o + 2) == 0):
            starts.add(int(m.group(2), 16))
    return sorted(starts)


def blitter_waits(ins):
    offs = sorted(ins)
    out = set()
    for i, o in enumerate(offs):
        if re.match(r'btst #14,(2\(a\d\)|0xdff002)$', ins[o]):
            out.add(o)
            if i + 1 < len(offs) and ins[offs[i + 1]].startswith('bne'):
                out.add(offs[i + 1])
    return out


def kind(o, ins, waits):
    if o is None:
        return 'outside gs2.run'
    if o in CAP_SPIN:
        return 'frame-cap spin'
    if o in VBL_WAIT:
        return 'VBL wait'
    if o in waits:
        return 'blitter-wait loops'
    t = ins.get(o, '')
    if '(sp)' in t or t.startswith(('bsr', 'jsr', 'rts')):
        return 'stack and call instructions'
    return 'other gs2.run code'


def report(out, top=15):
    out = Path(out)
    layout = json.loads((out / 'layout.json').read_text())
    base, size = layout['hunks']['0']['base'], layout['hunks']['0']['size']
    ins, rel = listing(out)
    waits = blitter_waits(ins)
    lines = []
    for seg in ('f5', 'f6'):
        p = out / f'{seg}.prof'
        if not p.exists():
            continue
        text = p.read_text()
        # The installed aprof build names its format AITDPROF; the layout is APROF 1's.
        h, pcs, nodes = aprof.parse_profile(re.sub(r'^\w*PROF 1', 'APROF 1', text, count=1))
        tot = h['units']
        mhz = h['colorclock_hz'] * h['CYCLE_UNIT'] / h['cycleunit'] / 1e6
        targets = [n[1] - base for n in nodes.values() if base <= n[1] < base + size]
        starts = routines(ins, rel, targets)
        # The slave's routines that replace the game's (gs2.slave_jumps): PCs from each, up to
        # 2 KB on, are named after the game's routine.
        jumps = sorted((t, int(o, 16)) for o, t in layout.get('slave_jumps', {}).items())
        frames = pcs.get(base + PRESENT, (0, 0))[1]
        fps = frames * 50 / h['vsyncs']
        byk, chipk = collections.Counter(), collections.Counter()
        fself, fchip = collections.Counter(), collections.Counter()
        for pc, (units, _execs, chip, _acc) in pcs.items():
            o = pc - base if base <= pc < base + size else None
            k = kind(o, ins, waits)
            byk[k] += units
            chipk[k] += chip
            if o is None:
                r = 'outside'
                i = bisect.bisect_right([t for t, _ in jumps], pc) - 1
                if i >= 0 and pc - jumps[i][0] < 0x800:
                    r = f'slave {jumps[i][1]:#x}'
            else:
                r = starts[bisect.bisect_right(starts, o) - 1]
            fself[r] += units
            fchip[r] += chip
        cacr = h['cacr']
        lines.append(f'== {seg}: {h["vsyncs"]} fields, {h["cpu_model"]} at {mhz:.1f} MHz, CACR ${cacr:04x} '
                     f'(IC {"on" if cacr & 1 else "off"}, DC {"on" if cacr & 0x100 else "off"})')
        lines.append(f'   {frames} frames: {fps:.2f} fps; chip-bus accesses {h["chip_units"] / tot:.1%} of the time')
        for k, v in byk.most_common():
            lines.append(f'   {k:30s} {v / tot:6.1%}   chip bus {chipk[k] / tot:6.1%}')
        lines.append(f'   routines by self time (code offset, share, chip-bus part):')
        for r, v in fself.most_common(top):
            name = r if isinstance(r, str) else f'${r:05x}'
            lines.append(f'     {name:>8s} {v / tot:6.1%}  {fchip[r] / tot:6.1%}')
    text = '\n'.join(lines) + '\n'
    (out / 'report.txt').write_text(text)
    return text


if __name__ == '__main__':
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    print(report(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 15), end='')
