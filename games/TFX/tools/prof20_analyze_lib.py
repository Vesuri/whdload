"""Shared profile loading and PC-to-region attribution for prof20_* tools."""
import csv, json, re, struct, bisect, collections
from pathlib import Path

F = ['n', 'fetch', 'body', 'special', 'pad', 'reads', 'writes', 'rb', 'wb', 'chipr', 'chipw', 'chiprb', 'chipwb']
MANUAL = {0x4e53a: 'CPU masked sprite merge', 0x3b93a: 'SuperShape view dispatcher', 0x77c8: 'aircraft list update loop',
          0x249a: 'RGB palette blend loop', 0x4bdca: 'integer sqrt', 0x4b774: 'matrix angle helper',
          0x3f51e: 'shape handle lookup', 0x3bc56: 'nested SuperShape dispatcher', 0x3d032: 'SuperShape part eval',
          0x7d90: 'aircraft iterator DBF8', 0x7d54: 'aircraft iterator DB30', 0x39cac: 'viewport scale calc'}


class Context:
    def __init__(self, p, lst):
        p = Path(p); root = Path(__file__).resolve().parents[1]
        rows = list(csv.reader((p / 'profile.csv').open()))
        meta = list(map(int, rows[0][1:]))
        self.duration = meta[1] - meta[0]; self.frames = meta[2]; self.div = meta[3]
        self.pcs = {int(r[1]): dict(zip(F, map(int, r[2:]))) for r in rows if r[0] == 'pc'}
        # A known stop-boundary residual of up to 512 scheduler ticks can remain unattributed.
        assert 0 <= self.duration - sum(self.emu_cost(v) for v in self.pcs.values()) <= 1024
        self.calls = collections.Counter()
        for r in rows:
            if r[0] == 'call': self.calls[int(r[2])] += int(r[3])
        self.call_edges = [(int(r[1]), int(r[2]), int(r[3])) for r in rows if r[0] == 'call']
        self.bases = json.loads((p / 'segments.json').read_text()); self.base = self.bases[0]
        self.code = (p / 'entry-hunk0.bin').read_bytes()
        text = Path(lst).read_text(encoding='latin1')
        ssym = {m[1]: int(m[2], 16) for m in re.finditer(r'^([A-Za-z_.][\w.]*)\s+00:([0-9A-Fa-f]{8})$', text, re.M)}
        self.sb = struct.unpack_from('>I', self.code, 0x19fe)[0] - ssym['do_swap_screen']
        self.slabels = sorted((a, n) for n, a in ssym.items() if a < 0x10000)
        self.slabel_addrs = [a for a, _ in self.slabels]
        self.spans = sorted((s['target'], s['size'], s['name']) for s in json.loads((root / 'tmp/step6/exact-symbol-spans.json').read_text()))
        self.starts = [s[0] for s in self.spans]
        self.targets = sorted(t - self.base for t in self.calls if self.base <= t < self.base + len(self.code))

    @staticmethod
    def emu_cost(v):
        return v['fetch'] + v['body'] + v['special'] + v['pad']

    def region(self, pc):
        o = pc - self.base
        if 0 <= o < len(self.code):
            i = bisect.bisect_right(self.starts, o) - 1
            if i >= 0 and o < self.spans[i][0] + self.spans[i][1]: return 'game', self.spans[i][2], self.spans[i][0]
            j = bisect.bisect_right(self.targets, o) - 1
            t = self.targets[j] if j >= 0 else 0
            return 'game', MANUAL.get(t, f'game:${t:x}'), t
        o = pc - self.sb
        if 0 <= o < 0x10000:
            i = bisect.bisect_right(self.slabel_addrs, o) - 1
            return 'slave', 'slave:' + self.slabels[i][1], self.slabels[i][0]
        if pc < 0x400: return 'lowpage', f'lowpage:${pc & ~0xf:x}', pc & ~0xf
        if 0xf80000 <= pc < 0x1000000: return 'rom', 'kickstart', 0
        for k, b in enumerate(self.bases[1:], 1):
            if b <= pc < b + 0x40000: return 'game', f'hunk{k}', 0
        return 'other', f'other:${pc & ~0xfff:x}', 0
