#!/usr/bin/env python3
"""Byte-level data flow of the CPU's chip accesses in Barto traces.

For every CPU data access (not code fetches) to an address in WATCH, records who made it:
(top-level main-loop routine, the instruction's PC, read or write, access size). The call
stack and the slot-to-instruction mapping are tools/chipprofile.py's. Kept per address, so a
question such as "does anything write the table at $E408" or "which routines write $11E36" is
a lookup.

    red = DataFlow(); red.feed(trace); red.save(path)        (tools/bench.py does this)
    python3 tools/dataflow.py OUT/flow.pkl.gz LO HI          accesses to [LO, HI), by address
    python3 tools/dataflow.py OUT/flow.pkl.gz --writers      written ranges per top-level routine

Tops are routine addresses (int) or 'irq' (interrupt level above 2) or 'main' (no call).
Fed with traces of the Enhanced copy, PCs are mapped back to chip addresses by MAP (a callable).
"""
import collections
import gzip
import os
import pickle
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
from amigaxdev import barto  # noqa: E402
import chipprofile  # noqa: E402

# Base memory below the screens: the low page, the object arrays and tables, the program
# with its variables, the copper lists and tables up to $13000; and the stack page.
WATCH = [(0x0, 0x13000), (0x7FD00, 0x80000)]
IPL_MAIN = 2


class DataFlow:
    def __init__(self, map_pc=None):
        self.acc = collections.defaultdict(collections.Counter)  # addr -> (top, pc, 'R'/'W', size) -> n
        self.fields = 0
        self.map_pc = map_pc
        self._stack, self._sps, self._pend = (), (), 0

    def feed(self, trace):
        t = barto.load(str(trace)) if not isinstance(trace, barto.Trace) else trace
        d, u, cache = t.data, struct.unpack_from, {}
        mp = self.map_pc or (lambda pc: pc)
        stack, sps, pend = self._stack, self._sps, self._pend
        lo = np.array([a for a, _ in WATCH])
        hi = np.array([b for _, b in WATCH])
        for f in t.fields:
            dt = np.dtype({'names': ['reg', 'size', 'addr', 'type', 'extra'],
                           'formats': ['<u2', '<u2', '<u4', 'u1', 'u1'],
                           'offsets': [0, 10, 12, 29, 31], 'itemsize': f.dma_size})
            recs = np.frombuffer(f.dma, dtype=dt)
            starts, tops, pcs = [], [], []
            off, end, pos = f.insn_off, f.insn_end, 0
            last_top, last_pc = 'none', 0
            in_irq, irq_entry = False, None
            while off < end:
                pc = None
                while True:
                    v = u('<I', d, off)[0]
                    off += 4
                    if v >= 0xffff0000:
                        break
                    if pc is None:
                        pc = v
                c = 0xffffffff - v
                sp = u('<I', d, off + 60)[0]
                sr = u('<I', d, off + 64)[0]
                off += 68
                if pc is None or pc == 0x7fffffff:
                    pend = 0
                    starts.append(pos)
                    tops.append(last_top)
                    pcs.append(last_pc)
                    pos += c
                    continue
                while sps and sp > sps[-1]:
                    stack, sps = stack[:-1], sps[:-1]
                cpc = mp(pc)
                if pend == 1:
                    stack, sps = stack + (cpc,), sps + (sp,)
                if (sr >> 8) & 7 > IPL_MAIN:
                    if not in_irq:
                        in_irq, irq_entry = True, cpc
                    top = 'irq'
                else:
                    in_irq = False
                    top = stack[0] if stack else 'main'
                last_top, last_pc = top, cpc
                starts.append(pos)
                tops.append(top)
                pcs.append(cpc)
                pos += c
                pend = chipprofile._opkind(t, pc, cache) if pc < len(t.chip) else 0
            n = len(recs)
            self.fields += 1
            if not starts or not n:
                continue
            st = np.asarray(starts, dtype=np.float64) * (n / max(pos, 1))
            own = np.clip(np.searchsorted(st, np.arange(n), side='right') - 1, 0, None)
            reg, addr = recs['reg'], recs['addr']
            cpu = (recs['type'] == 2) & ((reg & 0xfe00) == 0x1000) & \
                ~(((reg & 0x100) == 0) & (recs['extra'] == 0))
            inw = np.zeros(n, dtype=bool)
            for a, b in zip(lo, hi):
                inw |= (addr >= a) & (addr < b)
            sel = np.nonzero(cpu & inw)[0]
            if not len(sel):
                continue
            w = (reg[sel] & 0x100) != 0
            key = np.stack([addr[sel].astype(np.int64), own[sel].astype(np.int64),
                            w.astype(np.int64), recs['size'][sel].astype(np.int64)], axis=1)
            uk, cnt = np.unique(key, axis=0, return_counts=True)
            for (a, o, wr, sz), k in zip(uk.tolist(), cnt.tolist()):
                self.acc[a][(tops[o], pcs[o], 'W' if wr else 'R', sz)] += k
        self._stack, self._sps, self._pend = stack, sps, pend
        return t

    def save(self, path):
        with gzip.open(path, 'wb') as f:
            pickle.dump({'acc': dict(self.acc), 'fields': self.fields}, f)

    @classmethod
    def load(cls, path):
        r = cls()
        with gzip.open(path, 'rb') as f:
            s = pickle.load(f)
        r.acc.update(s['acc'])
        r.fields = s['fields']
        return r

    # -- queries ---------------------------------------------------------------------------

    def bytes_of(self, kind):
        """Every byte address accessed with KIND ('R' or 'W'), with its tops. An access of size
        2 or 4 covers that many bytes from its address."""
        out = collections.defaultdict(set)
        for a, c in self.acc.items():
            for (top, pc, k, sz), _ in c.items():
                if k == kind:
                    for b in range(a, a + max(1, sz)):
                        out[b].add(top)
        return out

    def writers(self):
        """top -> set of byte addresses it writes."""
        out = collections.defaultdict(set)
        for b, tops in self.bytes_of('W').items():
            for t in tops:
                out[t].add(b)
        return out


def ranges(addrs):
    out = []
    for a in sorted(addrs):
        if out and out[-1][1] == a:
            out[-1][1] = a + 1
        else:
            out.append([a, a + 1])
    return out


def lab(top):
    return top if isinstance(top, str) else f'${top:05x}'


def main(argv):
    r = DataFlow.load(argv[0])
    if argv[1:] == ['--writers']:
        for top, bs in sorted(r.writers().items(), key=lambda x: str(x[0])):
            rs = ranges(bs)
            print(f'{lab(top):8} {len(bs):6} bytes: ' + ', '.join(f'${a:05x}-${b - 1:05x}' for a, b in rs[:60])
                  + (f' ... ({len(rs)} ranges)' if len(rs) > 60 else ''))
        return
    lo, hi = int(argv[1], 16), int(argv[2], 16)
    for a in sorted(x for x in r.acc if lo <= x < hi):
        items = sorted(r.acc[a].items(), key=lambda x: -x[1])
        print(f'${a:05x}  ' + '  '.join(f'{k}{sz} {lab(t)}@{pc:05x} x{n}' for (t, pc, k, sz), n in items[:8]))


if __name__ == '__main__':
    main(sys.argv[1:])
