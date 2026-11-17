#!/usr/bin/env python3
"""Call profiles of Zany Golf traces: amigaxdev.callprofile with one call stack per CPU mode.

The game's main code runs in user mode on a stack below $10000, its interrupt handler
(WHDLoad's entry in fast memory, then the game's $121e6) in supervisor mode on WHDLoad's
stack near the top of chip memory. callprofile keeps one stack and pops a frame only when SP
rises above it, so with the user stack below the supervisor stack no interrupt frame ever
pops. Here a frame goes on the stack of the mode it runs in, and the supervisor stack empties
when the CPU returns to user mode. Interrupts are their own roots (`IRQ <entry>`).

    python3 tools/profile.py TRACE...       call tree, self cycles, DMA slot shares
    from profile import TwoStack            (Reduction API: feed, tree, inclusive, ...)
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
from amigaxdev import barto  # noqa: E402
from amigaxdev.callprofile import Reduction, _opkind  # noqa: E402


class TwoStack(Reduction):
    def __init__(self, marks=None, tally=(), split=None, page=0x100, watch=()):
        """split: a PC whose executions end an interval; self cycles are also kept per
        interval and per `page`-byte block of PCs in self.intervals, and the executions of
        each `watch` PC as key ('n', PC)."""
        super().__init__(marks, tally)
        self._ust, self._usp = (), ()
        self._sst, self._ssp = (), ()
        self.split, self.page, self.watch = split, page, set(watch)
        self.intervals = [collections.Counter()]

    def feed(self, trace):
        t = barto.load(str(trace)) if not isinstance(trace, barto.Trace) else trace
        d, u, cache = t.data, struct.unpack_from, {}
        ust, usp, sst, ssp = self._ust, self._usp, self._sst, self._ssp
        pend, pos, tallied = self._pend, self.pos, self.tallied
        tally, stacks, selfc, counts, events = self.tally, self.stacks, self.self, self.counts, self.events
        marks = {pc: name for name, pc in self.marks.items()}
        split, mask, iv, watch = self.split, ~(self.page - 1), self.intervals, self.watch
        cur = iv[-1]
        sup = False
        for f in t.fields:
            off, end = f.insn_off, f.insn_end
            tot = nopc = gap = 0
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
                sp, sr = u('<II', d, off + 60)
                off += 68
                tot += c
                pos += c
                if pc is None:
                    nopc += c
                    stacks[(('user',) + ust if not sup else ('super',) + sst) + ('stop',)] += c
                    continue
                if pc == 0x7fffffff:
                    gap += c
                    pend = 3
                    stacks[('super',) + sst + ('exception',)] += c
                    continue
                sup = bool(sr & 0x2000)
                if sup:
                    if pend == 3 and not sst:
                        ssp = ()
                    while ssp and sp > ssp[-1]:
                        sst, ssp = sst[:-1], ssp[:-1]
                    if pend == 1:
                        sst, ssp = sst + (pc,), ssp + (sp,)
                    elif pend == 3:
                        sst, ssp = sst + (('irq', pc),), ssp + (sp,)
                    key = ('super',) + sst
                else:
                    sst, ssp = (), ()
                    while usp and sp > usp[-1]:
                        ust, usp = ust[:-1], usp[:-1]
                    if pend == 1:
                        ust, usp = ust + (pc,), usp + (sp,)
                    key = ('user',) + ust
                if pc in marks:
                    events.append((marks[pc], pos - c, tallied))
                if pc in tally:
                    tallied += c
                if pc == split:
                    cur = collections.Counter()
                    iv.append(cur)
                cur[pc & mask] += c
                if pc in watch:
                    cur[('n', pc)] += 1
                selfc[pc] += c
                counts[pc] += 1
                stacks[key] += c
                pend = _opkind(t, pc, cache)
            dma = collections.Counter(f.dma[i + 29] for i in range(0, len(f.dma), f.dma_size))
            self.fields.append(dict(cycles=f.cycles, idle=f.idle, total=tot, nopc=nopc, gap=gap,
                                    dma=dict(dma)))
        self._ust, self._usp, self._sst, self._ssp = ust, usp, sst, ssp
        self._pend, self.pos, self.tallied = pend, pos, tallied
        return t


def main(paths):
    r = TwoStack()
    for p in paths:
        r.feed(p)
    tot = r.total()
    print(f'fields {len(r.fields)}  traced cycles {tot}')
    print(r.tree(label=lambda pc: f'{pc:06x}', min_share=0.005, depth=10))
    print('DMA slots: ' + ', '.join(f'{k} {v:.1%}' for k, v in r.dma_shares().items()))
    print('self cycles by PC (top 25):')
    for pc, c in r.self.most_common(25):
        print(f'  {pc:06x}  {100 * c / tot:5.2f}%  x{r.counts[pc]}')


if __name__ == '__main__':
    main(sys.argv[1:])
