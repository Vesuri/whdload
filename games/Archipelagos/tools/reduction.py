#!/usr/bin/env python3
"""amigaxdev.callprofile's Reduction with this game's interrupts found by their handlers.

The trace marks cycles between instrumented instructions with the PC 0x7fffffff. The shared
reduction takes each such gap for an exception entry and pushes an interrupt frame. On the
68030 core most gaps are CPU overhead inside ordinary code (SP unchanged), and those frames
nest the renderer under dozens of bogus interrupts. And on a 68010+ WHDLoad takes the
interrupts through its own vector table (VBR) in fast memory, which enters the game's
handler with an rts. So here every gap's cycles go to the running code, and an interrupt
frame starts where the game's handler starts: at a handler in the vector table ($64-$7c in
the trace's chip snapshot) not reached by a call. WHDLoad's dispatch before it is billed to
the interrupted code (it is in fast memory: the report's regions show it).

    from reduction import GameReduction       # same API and saved form as Reduction
"""
import collections
import os
import struct
import sys

sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
from amigaxdev import barto  # noqa: E402
from amigaxdev.callprofile import Reduction, _opkind  # noqa: E402


class GameReduction(Reduction):
    def __init__(self, marks=None, tally=()):
        super().__init__(marks, tally)
        self.gaps = 0          # cycles of the trace's gap records (billed to the running code)
        self.irqs = collections.Counter()   # handler entry -> entries

    def feed(self, trace):
        t = barto.load(str(trace)) if not isinstance(trace, barto.Trace) else trace
        if t.pc_base:
            raise ValueError('relative-PC traces (.pc-base) are not supported')
        handlers = {struct.unpack_from('>I', t.chip, v)[0] for v in range(0x64, 0x80, 4)} - {0}
        d, u, cache = t.data, struct.unpack_from, {}
        stack, sps, pend, pos, tallied = self._stack, self._sps, self._pend, self.pos, self.tallied
        tally = self.tally
        stacks, selfc, counts, events = self.stacks, self.self, self.counts, self.events
        marks = {pc: name for name, pc in self.marks.items()}
        gapc = 0
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
                sp = u('<I', d, off + 60)[0]
                off += 68
                tot += c
                pos += c
                if pc is None:
                    nopc += c
                    stacks[stack + ('stop',)] += c
                    continue
                if pc == 0x7fffffff:
                    gap += c
                    gapc += c
                    continue
                while sps and sp > sps[-1]:
                    stack, sps = stack[:-1], sps[:-1]
                if gapc:
                    stacks[stack] += gapc
                    self.gaps += gapc
                    gapc = 0
                if pc in handlers and pend != 1:
                    stack, sps = stack + (('irq', pc),), sps + (sp,)
                    self.irqs[pc] += 1
                if pend == 1:
                    stack, sps = stack + (pc,), sps + (sp,)
                if pc in marks:
                    events.append((marks[pc], pos - c, tallied))
                if pc in tally:
                    tallied += c
                selfc[pc] += c
                counts[pc] += 1
                stacks[stack] += c
                pend = _opkind(t, pc, cache)
            dma = collections.Counter(f.dma[i + 29] for i in range(0, len(f.dma), f.dma_size))
            self.fields.append(dict(cycles=f.cycles, idle=f.idle, total=tot, nopc=nopc, gap=gap,
                                    dma=dict(dma)))
        if gapc:
            stacks[stack] += gapc
            self.gaps += gapc
        self._stack, self._sps, self._pend, self.pos, self.tallied = stack, sps, pend, pos, tallied
        return t
