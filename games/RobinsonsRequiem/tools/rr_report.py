#!/usr/bin/env python3
"""Where the frame time goes in a tools/rr_prof.py run: rr_report.py OUT [N]

Self time per function, the N largest (default 16): every PC is charged to the nearest call
target at or below it in its START hunk, so a function's figure includes the loops and jump
tables placed after its entry. The call targets are the run's own: aprof's call records, or
the entries a Barto trace's reduction pushed (its call stacks themselves do not hold in the
ECS game, whose interrupts run on another stack). PCs outside START are grouped by 4 KB.
ms/frame is per frame drawn in the window (run.json `frames`), 20 ms per PAL field.

aprof runs (OUT/window.prof) add the time in the AGA game's waits (WAITS, SLAVE_WAITS) and the
rest, busy, per frame drawn; and chip memory: each function's share of time in chip
accesses and its accesses per frame, and in total the chunky-to-planar loop's accesses (AGA
hunk 2 +$2e84: byte reads of the chunky buffer, byte writes to the eight planes) against
the rest. Barto runs (OUT/window.pkl.gz) add the DMA slot shares and the frame intervals.
docs/performance.md has the runs this reports on.
"""
import bisect
import collections
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _amigaxdev  # noqa: F401,E402
from amigaxdev import aprof  # noqa: E402
from amigaxdev.callprofile import Reduction  # noqa: E402

# START's hunk sizes (docs/internals.md)
SIZES = {'RobinsonsRequiemAGA': (0x3a30, 0x103d8, 0x543c, 0x1154),
         'RobinsonsRequiem': (0x2f30, 0xea30, 0x1ec8, 0x10d0, 0x1154)}
# AGA hunk 2: the conversion loop's chunky reads (move.b (a0)+) and plane writes
C2P_READS = list(range(0x2e94, 0x2ea4, 2)) + list(range(0x2f6a, 0x2f7a, 2))
C2P_WRITES = (0x2f52, 0x2f56, 0x2f58, 0x2f5c, 0x2f5e, 0x2f62, 0x2f64, 0x2f68,
              0x3028, 0x302c, 0x302e, 0x3032, 0x3034, 0x3038, 0x303a, 0x303e)
# AGA waits, (hunk, first, end): the cap wait's loop, the copper-interrupt wait at the start
# of a 3D pass, the beam wait before the swap
WAITS = {'cap wait': (1, 0x49ee, 0x49f6), 'copper wait': (0, 0x13c0, 0x13ca),
         'beam wait': (0, 0x13ce, 0x13de)}
# and the slave's, between two of its labels (src/): the frame pacing's wait
SLAVE_WAITS = {'pacing wait': ('_pacewait', '_pacedone')}


def slave_waits(run):
    """SLAVE_WAITS as absolute ranges, from the build's listing while it is still the slave
    the run used (run.json's slave address and slave_sha256)."""
    env = run['env']
    lst = ROOT / 'tmp/build' / env['BUILD'] / f"{env['VARIANT']}.lst"
    slave = lst.with_suffix('.Slave')
    if 'slave' not in run or not lst.exists() or not slave.exists() \
            or hashlib.sha256(slave.read_bytes()).hexdigest() != run['slave_sha256']:
        return {}
    syms = {}
    for line in lst.read_text(encoding='latin1').splitlines():
        f = line.split()
        if len(f) == 2 and f[1].startswith('00:'):
            syms[f[0]] = int(f[1][3:], 16)
    base = int(run['slave'], 16)
    return {w: (base + syms[a], base + syms[b]) for w, (a, b) in SLAVE_WAITS.items()
            if a in syms and b in syms}


class Hunks:
    def __init__(self, run):
        self.bases = [int(x, 16) for x in run['hunks']]
        self.sizes = SIZES[run['env']['VARIANT']]
        self.starts = collections.defaultdict(set)

    def where(self, pc):
        for i, (b, s) in enumerate(zip(self.bases, self.sizes)):
            if b <= pc < b + s:
                return i, pc - b
        return None, pc

    def entry(self, pc):
        self.starts[self.where(pc)[0]].add(self.where(pc)[1])

    def function(self, pc):
        h, o = self.where(pc)
        if h is None:
            return None, pc & ~0xfff
        s = sorted(self.starts[h])
        i = bisect.bisect_right(s, o) - 1
        return h, s[i] if i >= 0 else 0

    @staticmethod
    def name(key):
        h, o = key
        return f'h{h}+${o:05x}' if h is not None else f'${o:06x}'


def report(out, n):
    out = Path(out)
    run = json.loads((out / 'run.json').read_text())
    fields = run['window'][1] - run['window'][0]
    frames = run['frames']
    hk = Hunks(run)
    self_t, chip_t, chip_n, calls, insns = (collections.Counter() for _ in range(5))
    if (out / 'window.prof').exists():
        text = (out / 'window.prof').read_text().replace('AITDPROF 1', 'APROF 1', 1)
        head, pcs, nodes = aprof.parse_profile(text)
        for _, (_, target, _, _, c) in nodes.items():
            hk.entry(target)
            calls[hk.function(target)] += c
        total = head['units']
        for pc, (u, e, cu, ca) in pcs.items():
            k = hk.function(pc)
            self_t[k] += u
            chip_t[k] += cu
            chip_n[k] += ca
        kind = 'aprof'
    else:
        r = Reduction.load(out / 'window.pkl.gz')
        for st in r.stacks:
            for fr in st:
                if isinstance(fr, tuple):
                    hk.entry(fr[1])
                elif isinstance(fr, int):
                    hk.entry(fr)
        total = r.total()
        for pc, c in r.self.items():
            k = hk.function(pc)
            self_t[k] += c
            insns[k] += r.counts[pc]
        kind = 'barto'
    ms = 20 * fields / total / max(frames, 1)     # per unit of the profile, per frame
    env = run['env']
    print(f"{env['VARIANT']} {env['BUILD']} on {env['SETUP']} ({kind}"
          f"{', ' + run['extra_args'] if run.get('extra_args') else ''}): {frames} frames in "
          f"{fields} fields, {50 * frames / fields:.2f} fps, {total * ms:.1f} ms/frame")
    if kind == 'aprof':
        chip = sum(v[2] for v in pcs.values())
        acc = sum(v[3] for v in pcs.values())
        print(f'  chip accesses {chip * ms:.1f} ms/frame ({acc / frames:.0f} per frame), '
              f'the rest {(total - chip) * ms:.1f} ms')
        if env['VARIANT'] == 'RobinsonsRequiemAGA':
            waits = {w: sum(v[0] for pc, v in pcs.items()
                            if hk.bases[h] + a <= pc < hk.bases[h] + b)
                     for w, (h, a, b) in WAITS.items()}
            waits.update({w: sum(v[0] for pc, v in pcs.items() if a <= pc < b)
                          for w, (a, b) in slave_waits(run).items()})
            print('  waits ' + ', '.join(f'{w} {u * ms:.1f}' for w, u in waits.items())
                  + f' ms; busy {(total - sum(waits.values())) * ms:.1f} ms/frame')
            for what, offs in (('c2p plane writes', C2P_WRITES), ('c2p chunky reads', C2P_READS)):
                ps = [pcs[hk.bases[2] + o] for o in offs if hk.bases[2] + o in pcs]
                print(f'    {what}: {sum(p[2] for p in ps) * ms:.1f} ms '
                      f'({sum(p[3] for p in ps) / frames:.0f} accesses/frame)')
        print(f'  {"function":12} {"share":>6} {"ms/frame":>8} {"chip%":>6} '
              f'{"chip acc/frame":>14} {"calls/frame":>11}')
        for k, u in self_t.most_common(n):
            print(f'  {hk.name(k):12} {u / total * 100:5.1f}% {u * ms:8.1f} '
                  f'{chip_t[k] / max(u, 1) * 100:6.1f} {chip_n[k] / frames:14.0f} '
                  f'{calls[k] / frames:11.1f}')
    else:
        dma = {k: round(v * 100, 1) for k, v in r.dma_shares().items()}
        print(f'  DMA slots %: {dma}')
        pos = [e[1] for e in r.events if e[0] == 'frame']
        per_field = total / len(r.fields)
        gaps = [(b - a) / per_field for a, b in zip(pos, pos[1:])]
        if gaps:
            print(f'  fields per frame: {min(gaps):.1f} to {max(gaps):.1f}')
        print(f'  {"function":12} {"share":>6} {"ms/frame":>8} {"insns/frame":>11}')
        for k, c in self_t.most_common(n):
            print(f'  {hk.name(k):12} {c / total * 100:5.1f}% {c * ms:8.1f} '
                  f'{insns[k] / frames:11.0f}')


if __name__ == '__main__':
    report(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 16)
