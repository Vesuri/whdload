#!/usr/bin/env python3
"""Split a capture's interrupt cycles by source and handler.

  python3 tools/interrupt_profile.py CAPTURE [--listing EXACT.lst] [--out report.json]

CAPTURE is a fixed_window.py directory with trace.bin, code.bin and slave.slave. Every
Kickstart 1.3 autovector entry (KickEmu's RAM copy) starts a dispatch; the exception gap
before it, the autovector, the handler and ExitIntr belong to it until its RTE. Nested
dispatches are separated by stack depth. A dispatch's source is the INTREQ bit whose
vector it jumps through; CIA-B dispatches are further split by the cia.resource ICR bit.
Supervisor time outside any dispatch (traps, Supervisor()) is reported as `other`.

Inclusive cycles per handler routine follow observed calls (bsr/jsr, and the autovector's
pea/jmp into the handler). BLIT interrupts are attributed to the interrupted main-context
call chain, and to whether the slave's polygon wrapper (s60_polygon, from --listing) was
active. Register snapshots precede their instruction (stellar7_report convention).
"""
import argparse
import collections
import json
import os
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev import barto

KICK = 0xfc0000
# Autovector entries (Kickstart 1.3 offsets) and the source each vector jump serves.
ENTRIES = {0xfc0c8e: 1, 0xfc0ce2: 2, 0xfc0d14: 3, 0xfc0d6c: 4, 0xfc0dfa: 5, 0xfc0e40: 6,
           0xfc0e86: 7}
SOURCES = {0xfc0cba: 'TBE', 0xfc0ccc: 'DSKBLK', 0xfc0cde: 'SOFT', 0xfc0d0e: 'PORTS',
           0xfc0d42: 'BLIT', 0xfc0d54: 'VERTB', 0xfc0d66: 'COPER', 0xfc0d9c: 'AUD1',
           0xfc0db0: 'AUD3', 0xfc0dc4: 'AUD0', 0xfc0dd8: 'AUD2', 0xfc0e28: 'DSKSYNC',
           0xfc0e3a: 'RBF', 0xfc0e6e: 'INTEN', 0xfc0e80: 'EXTER', 0xfc0e94: 'NMI'}
# cia.resource ICR dispatch (CIA-B entry $4678, CIA-A $4684): the jsr for each ICR bit.
CIA_BITS = {0xfc46cc: 'TA', 0xfc46d6: 'TB', 0xfc46e0: 'ALRM', 0xfc46ea: 'SP', 0xfc46f4: 'FLG'}
CIAB_ENTRY, CIAA_ENTRY = 0xfc4678, 0xfc4684


def listing_symbol(listing, name):
    match = re.search(rb'^' + name.encode() + rb'\s+00:([0-9A-F]{8})$', Path(listing).read_bytes(), re.M)
    return int(match[1], 16) if match else None


def is_call(op):
    return (op & 0xff00) == 0x6100 or (op & 0xffc0) == 0x4e80


def analyse(capture, listing=None):
    capture = Path(capture)
    os.environ['SLAVE'] = str(capture/'slave.slave')
    import stellar7_report as report
    meta = json.loads((capture/'metadata.json').read_text())
    base = meta.get('base', 0xc00000)
    trace = barto.load(capture/'trace.bin')
    dump = (capture/'code.bin').read_bytes()
    mem = report.Memory(trace, dump, base)
    regions = report.regions(dump, base, trace.chip)
    namer = report.Namer(regions, mem)
    kick = next(r for r in regions if r[2] == 'kick')
    slave = next(r for r in regions if r[2] == 'slave')
    to_kick = lambda pc: pc - kick[3] if kick[0] <= pc < kick[1] else None
    polygon = None
    if listing:
        offset = listing_symbol(listing, 's60_polygon')
        if offset is not None:
            polygon = slave[0] + offset
    execbase = mem.long(4)
    ssp_lo, ssp_hi = mem.long(execbase + 58), mem.long(execbase + 54)
    main_range = report.contexts(trace, trace.fields)[0]

    total = 0
    by_source = collections.Counter()      # source -> cycles
    count = collections.Counter()          # source -> dispatches
    handler_incl = collections.defaultdict(collections.Counter)  # source -> path -> cycles
    handler_calls = collections.defaultdict(collections.Counter)
    region_cycles = collections.defaultdict(collections.Counter)  # source -> region -> cycles
    blit_callers = collections.Counter()
    blit_inside = collections.Counter()
    other = 0
    gap = 0
    stack = []          # active dispatches: dict(s0, source, frames, pending, cycles)
    main_frames = []    # interrupted main-context call chain: [(psp, name)]
    main_pending = None
    finished = []

    def close(d):
        source = d['source'] or f"L{d['level']}?"
        by_source[source] += d['cycles']
        count[source] += 1
        for path, cycles in d['paths'].items():
            handler_incl[source][path] += cycles
        for path, n in d['calls'].items():
            handler_calls[source][path] += n
        for region, cycles in d['regions'].items():
            region_cycles[source][region] += cycles
        if source == 'BLIT':
            chain = d['main']
            names = [name for _, name in chain]
            inside = polygon is not None and any(name == namer.addr(polygon) for name in names)
            blit_inside['inside' if inside else 'outside'] += 1
            if not inside:
                blit_callers[' > '.join(names[-3:]) or '[top]'] += 1
        finished.append(source)

    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            total += cost
            sp = regs[15]
            if pc is None or pc == 0x7fffffff:
                gap += cost
                continue
            cost, gap = cost + gap, 0
            supervisor = ssp_lo <= sp < ssp_hi
            while stack and (not supervisor or sp > stack[-1]['s0']):
                close(stack.pop())
            if not supervisor:
                if main_range[0] <= sp < main_range[1] + 0x1000:
                    if main_pending is not None:
                        psp = main_pending
                        main_pending = None
                        if sp == psp - 4:
                            main_frames.append((psp, namer.addr(pc)))
                    while main_frames and sp >= main_frames[-1][0]:
                        main_frames.pop()
                    del main_frames[:-64]
                    op = mem.word(pc)
                    if op is not None and is_call(op):
                        main_pending = sp
                continue
            k = to_kick(pc)
            if k in ENTRIES:
                stack.append(dict(s0=sp, level=ENTRIES[k], source=None, cycles=0, frames=[],
                                  pending=None, paths=collections.Counter(),
                                  calls=collections.Counter(), regions=collections.Counter(),
                                  main=list(main_frames)))
            if not stack:
                other += cost
                continue
            d = stack[-1]
            d['cycles'] += cost
            d['regions'][namer.addr(pc).split(':')[0]] += cost
            frames = d['frames']
            if d['pending'] is not None:
                psp, kind = d['pending']
                d['pending'] = None
                if sp == psp - 4:
                    frames.append((psp, namer.addr(pc)))
                    d['calls'][tuple(name for _, name in frames)] += 1
            while frames and sp >= frames[-1][0]:
                frames.pop()
            if frames:
                seen = set()
                for depth in range(1, len(frames) + 1):
                    path = tuple(name for _, name in frames[:depth])
                    if path not in seen:
                        d['paths'][path] += cost
                        seen.add(path)
            if k in SOURCES and d['source'] is None:
                d['source'] = SOURCES[k]
                # pea return; jmp (a5): the handler returns to ExitIntr at sp+4.
                d['pending'] = (sp + 4, 'vector')
                continue
            if k in CIA_BITS:
                d['source'] = ('CIAB-' if d.get('cia') == 'B' else 'CIAA-') + CIA_BITS[k]
            if k == CIAB_ENTRY:
                d['cia'] = 'B'
            elif k == CIAA_ENTRY:
                d['cia'] = 'A'
            op = mem.word(pc)
            if op is not None and is_call(op):
                d['pending'] = (sp, 'call')
    while stack:
        close(stack.pop())

    fields = len(trace.fields)
    interrupt = sum(by_source.values())
    sources = []
    for source, cycles in by_source.most_common():
        n = count[source]
        handlers = []
        for path, incl in sorted(handler_incl[source].items(), key=lambda kv: -kv[1]):
            if len(path) > 4 or incl < 0.0005 * total:
                continue
            calls = handler_calls[source][path]
            handlers.append(dict(path=list(path), cycles_per_field=incl / fields,
                                 calls_per_field=calls / fields,
                                 cycles_per_call=incl / calls if calls else None,
                                 share=incl / total))
        sources.append(dict(source=source, dispatches_per_field=n / fields,
                            cycles_per_field=cycles / fields, cycles_per_dispatch=cycles / n,
                            share=cycles / total,
                            regions={k: v / fields for k, v in region_cycles[source].most_common()},
                            handlers=handlers))
    return dict(capture=str(capture), fields=fields, total_cycles=total,
                field_cycles=sum(f.cycles for f in trace.fields),
                interrupt_share=interrupt / total, other_supervisor_share=other / total,
                trailing_gap_cycles=gap, sources=sources,
                blit=dict(polygon_wrapper=namer.addr(polygon) if polygon else None,
                          inside_polygon=blit_inside['inside'],
                          outside_polygon=blit_inside['outside'],
                          outside_callers=[dict(chain=c, dispatches=n)
                                           for c, n in blit_callers.most_common(20)]))


def text(result):
    lines = [f"# {result['capture']}: {result['fields']} fields, {result['total_cycles']} cycles",
             f"interrupt dispatches {100 * result['interrupt_share']:.2f}%, "
             f"other supervisor {100 * result['other_supervisor_share']:.2f}%"]
    for s in result['sources']:
        lines.append(f"\n## {s['source']}: {100 * s['share']:.2f}%, {s['dispatches_per_field']:.2f}/field, "
                     f"{s['cycles_per_dispatch']:.0f} cycles/dispatch, {s['cycles_per_field']:.0f} cycles/field")
        lines.append('   regions/field: ' + ', '.join(f'{k} {v:.0f}' for k, v in s['regions'].items()))
        for h in s['handlers'][:24]:
            per_call = f"{h['cycles_per_call']:8.0f}" if h['cycles_per_call'] else '       -'
            lines.append(f"  {100 * h['share']:6.2f}% {h['calls_per_field']:6.2f}/field {per_call}/call  "
                         + ' > '.join(h['path']))
    b = result['blit']
    lines.append(f"\n## BLIT dispatches: inside {b['polygon_wrapper']} {b['inside_polygon']}, "
                 f"outside {b['outside_polygon']}")
    for c in b['outside_callers']:
        lines.append(f"  {c['dispatches']:6d}  {c['chain']}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('capture')
    parser.add_argument('--listing')
    parser.add_argument('--out')
    args = parser.parse_args()
    result = analyse(args.capture, args.listing)
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=1) + '\n')
    print(text(result))


if __name__ == '__main__':
    main()
