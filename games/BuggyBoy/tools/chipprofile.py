#!/usr/bin/env python3
"""Attribute every chip-bus access in Barto traces to the code that made it.

The game runs entirely in chip RAM, so every CPU access that misses the instruction cache is
a chip-bus slot in the trace's DMA records (one record per colour clock: CPU code fetch, data
read, data write, with the address). Instructions are mapped onto slots by their cycle
position within the field (an approximation of a few slots), and the call stack is rebuilt as
amigaxdev.callprofile does. Kept per run:

- per context (top-level main-loop routine, innermost function): CPU cycles, chip code
  fetches, data reads, data writes;
- per top-level routine: the 16-byte granules it reads and writes (its data flow);
- per DMA channel (bitplane, blitter A-D, copper, audio, sprite): the 256-byte pages it touches.

    red = ChipReduction(); red.feed(trace); red.save(path)       (tools/bench.py does this)
    python3 tools/chipprofile.py OUT/chip.pkl.gz                  report
"""
import collections
import gzip
import os
import pickle
import struct
import sys

import numpy as np

sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
from amigaxdev import barto  # noqa: E402

IPL_MAIN = 2   # the game's main code runs at SR $22xx; the level-3 handler (and WHDLoad's) above

DMA_NAMES = {1: 'refresh', 2: 'CPU', 3: 'copper', 4: 'audio', 5: 'blitter', 6: 'bitplane',
             7: 'sprite', 8: 'disk'}


def _opkind(t, pc, cache):
    k = cache.get(pc)
    if k is None:
        m = t.chip
        w = struct.unpack_from('>H', m, pc)[0] if pc + 2 <= len(m) else 0
        k = 1 if (w & 0xffc0) == 0x4e80 or (w & 0xff00) == 0x6100 else 0
        cache[pc] = k
    return k


class ChipReduction:
    def __init__(self):
        self.ctx = {}                        # (top, func) -> id
        self.cycles = collections.Counter()  # id -> CPU cycles
        self.acc = collections.Counter()     # (id, kind) -> chip accesses; kind code/read/write
        self.reads = collections.defaultdict(set)    # top -> 16-byte granules read
        self.writes = collections.defaultdict(set)   # top -> granules written
        self.wcount = collections.defaultdict(collections.Counter)  # top -> granule -> writes
        self.rcount = collections.defaultdict(collections.Counter)  # top -> granule -> reads
        self.ccount = collections.defaultdict(collections.Counter)  # top -> code granule -> fetches
        self.dma_pages = collections.defaultdict(set)  # (type, extra, 'r'/'w') -> 256-byte pages
        self.slots = collections.Counter()   # type -> slots
        self.fields = 0
        self._stack, self._sps, self._pend = (), (), 0

    def _id(self, top, func):
        k = (top, func)
        i = self.ctx.get(k)
        if i is None:
            i = self.ctx[k] = len(self.ctx)
        return i

    def feed(self, trace):
        t = barto.load(str(trace)) if not isinstance(trace, barto.Trace) else trace
        d, u, cache = t.data, struct.unpack_from, {}
        stack, sps, pend = self._stack, self._sps, self._pend
        for f in t.fields:
            dt2 = np.dtype({'names': ['reg', 'size', 'addr', 'type', 'extra'],
                            'formats': ['<u2', '<u2', '<u4', 'u1', 'u1'],
                            'offsets': [0, 10, 12, 29, 31], 'itemsize': f.dma_size})
            recs = np.frombuffer(f.dma, dtype=dt2)
            starts, ids = [], []
            off, end, pos = f.insn_off, f.insn_end, 0
            last = self._id('none', None)
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
                off += 68
                if pc is None or pc == 0x7fffffff:
                    # gaps are not reliably interrupt entries on the 68020/030 core (they also
                    # follow RTE): interrupts are told by the SR mask below instead
                    pend = 0
                    starts.append(pos)
                    ids.append(last)
                    self.cycles[last] += c
                    pos += c
                    continue
                while sps and sp > sps[-1]:
                    stack, sps = stack[:-1], sps[:-1]
                if pend == 1:
                    stack, sps = stack + (pc,), sps + (sp,)
                ipl = (u('<I', d, off - 4)[0] >> 8) & 7
                if ipl > IPL_MAIN:
                    if not in_irq:
                        in_irq, irq_entry = True, pc
                    top, func = 'irq', irq_entry
                elif stack:
                    top, func = stack[0], stack[-1]
                else:
                    top, func = 'main', None
                if ipl <= IPL_MAIN:
                    in_irq = False
                last = self._id(top, func)
                starts.append(pos)
                ids.append(last)
                self.cycles[last] += c
                pos += c
                pend = _opkind(t, pc, cache)
            n = len(recs)
            if not starts:
                continue
            starts = np.asarray(starts, dtype=np.float64) * (n / max(pos, 1))
            ids = np.asarray(ids)
            owner = ids[np.clip(np.searchsorted(starts, np.arange(n), side='right') - 1, 0, None)]
            typ = recs['type']
            for ty, cnt in zip(*np.unique(typ, return_counts=True)):
                self.slots[int(ty)] += int(cnt)
            cust = (typ == 2) & ((recs['reg'] & 0xfe00) != 0x1000) & (recs['reg'] < 0x200)
            for i, cnt in collections.Counter(owner[cust].tolist()).items():
                self.acc[(i, 'custom')] += cnt
            cpu = (typ == 2) & ((recs['reg'] & 0xfe00) == 0x1000)
            reg, addr, extra, own = recs['reg'][cpu], recs['addr'][cpu], recs['extra'][cpu], owner[cpu]
            write = (reg & 0x0100) != 0
            code = (extra == 0) & ~write
            kinds = np.where(write, 2, np.where(code, 0, 1))
            for (i, k), cnt in collections.Counter(zip(own.tolist(), kinds.tolist())).items():
                self.acc[(i, ('code', 'read', 'write')[k])] += cnt
            # data flow per top-level routine (16-byte granules)
            data = ~code
            if data.any():
                ids_d = own[data].astype(np.int64)
                key = (ids_d << 32) | (addr[data].astype(np.int64) >> 4) | (write[data].astype(np.int64) << 31)
                ukeys, cnts = np.unique(key, return_counts=True)
                inv = {v: k for k, v in self.ctx.items()}
                for k, cnt in zip(ukeys.tolist(), cnts.tolist()):
                    top = inv[k >> 32][0]
                    g = k & 0x7fffffff
                    if k & (1 << 31):
                        self.writes[top].add(g)
                        self.wcount[top][g] += cnt
                    else:
                        self.reads[top].add(g)
                        self.rcount[top][g] += cnt
            if code.any():
                ids_c = own[code].astype(np.int64)
                key = (ids_c << 32) | (addr[code].astype(np.int64) >> 4)
                ukeys, cnts = np.unique(key, return_counts=True)
                inv = {v: k for k, v in self.ctx.items()}
                for k, cnt in zip(ukeys.tolist(), cnts.tolist()):
                    self.ccount[inv[k >> 32][0]][k & 0xffffffff] += cnt
            # other DMA channels: 256-byte pages per (type, extra)
            oth = (typ > 2) & (recs['addr'] != 0xffffffff)
            if oth.any():
                key = (typ[oth].astype(np.int64) << 40) | (recs['extra'][oth].astype(np.int64) << 32) | \
                    (recs['addr'][oth].astype(np.int64) >> 8)
                for k in np.unique(key).tolist():
                    self.dma_pages[(k >> 40, (k >> 32) & 0xff)].add(k & 0xffffffff)
            self.fields += 1
        self._stack, self._sps, self._pend = stack, sps, pend
        return t

    def save(self, path):
        with gzip.open(path, 'wb') as f:
            pickle.dump(self.__dict__, f)

    @classmethod
    def load(cls, path):
        r = cls.__new__(cls)
        with gzip.open(path, 'rb') as f:
            r.__dict__.update(pickle.load(f))
        return r


def ranges(pages, shift):
    """Merge sorted page numbers into (start, end) address ranges."""
    out = []
    for p in sorted(pages):
        a = p << shift
        if out and out[-1][1] == a:
            out[-1][1] = a + (1 << shift)
        else:
            out.append([a, a + (1 << shift)])
    return out


def fmt_ranges(rs, limit=40):
    s = ', '.join(f'${a:05x}-${b - 1:05x}' for a, b in rs[:limit])
    return s + (f' ... ({len(rs)} ranges)' if len(rs) > limit else '')


def report(r, labels=None):
    labels = labels or {}
    lab = lambda x: x if isinstance(x, str) else (f'{x:06x} {labels.get(x, "")}'.rstrip())
    inv = {v: k for k, v in r.ctx.items()}
    out = [f'fields {r.fields}; chip slots: ' + ', '.join(
        f'{DMA_NAMES.get(k, k)} {v / max(1, sum(r.slots.values())):.1%}' for k, v in sorted(r.slots.items()))]
    tot_cyc = sum(r.cycles.values())
    # by top-level routine
    bytop = collections.defaultdict(lambda: collections.Counter())
    for i, c in r.cycles.items():
        bytop[inv[i][0]]['cycles'] += c
    for (i, k), c in r.acc.items():
        bytop[inv[i][0]][k] += c
    out.append('')
    out.append('per top-level routine (cycles share; chip accesses per field: code / read / write / '
               'custom registers; CPU cycles per access):')
    for top, s in sorted(bytop.items(), key=lambda x: -x[1]['cycles']):
        if s['cycles'] / tot_cyc < 0.002:
            continue
        a = s['code'] + s['read'] + s['write'] + s['custom']
        out.append(f'  {lab(top):28} {s["cycles"] / tot_cyc:6.1%}  {s["code"] / r.fields:7.0f} '
                   f'{s["read"] / r.fields:7.0f} {s["write"] / r.fields:7.0f} {s["custom"] / r.fields:6.0f}  '
                   f'{s["cycles"] / max(1, a):6.1f}')
    # by innermost function
    byf = collections.defaultdict(lambda: collections.Counter())
    for i, c in r.cycles.items():
        byf[inv[i][1]]['cycles'] += c
    for (i, k), c in r.acc.items():
        byf[inv[i][1]][k] += c
    out.append('')
    out.append('per innermost function (top 30 by cycles):')
    for fn, s in sorted(byf.items(), key=lambda x: -x[1]['cycles'])[:30]:
        a = s['code'] + s['read'] + s['write'] + s['custom']
        out.append(f'  {lab(fn) if fn is not None else "-":28} {s["cycles"] / tot_cyc:6.1%}  '
                   f'{s["code"] / r.fields:7.0f} {s["read"] / r.fields:7.0f} {s["write"] / r.fields:7.0f}'
                   f' {s["custom"] / r.fields:6.0f}  {s["cycles"] / max(1, a):6.1f}')
    out.append('')
    out.append('DMA channels, 256-byte pages touched:')
    for (ty, ex), pages in sorted(r.dma_pages.items()):
        out.append(f'  {DMA_NAMES.get(ty, ty)}/{ex}: {fmt_ranges(ranges(pages, 8))}')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    print(report(ChipReduction.load(sys.argv[1])), end='')
