#!/usr/bin/env python3
"""Report VERIFY_PHASE beam-clock phases; optionally compare the same trace window.

Usage: phase_report.py CAPTURE [--trace]
All phase costs are exclusive milliseconds per complete present-to-present frame.
The ring is read from the capture's initial/final memory snapshots. Overwritten
windows, ambiguous live headers and missing trace events are errors, not zeroes.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import statistics
import struct

MAX_CAPACITY = 16384
FIELD_CLOCKS = 142102  # 313 PAL lines * 227 colour clocks * 2
PAIRS = {1: ('world', 2), 3: ('render', 4), 5: ('wait', 6),
         7: ('copy', 8), 9: ('hud', 10), 11: ('timer', 12), 13: ('present', 14), 16: ('world', 15)}
ENDS = {end: start for start, (_, end) in PAIRS.items()}
ENDS[17] = 16  # Aborted world step; no completed tick.


def snapshot(path, final=False):
    prefix = 'final-' if final else ''
    base = int((path / 'dump-base.txt').read_text(), 0)
    memories = [(0, (path / (prefix + 'chip.bin')).read_bytes()),
                (base, (path / (prefix + 'code.bin')).read_bytes())]
    headers = []
    for origin, data in memories:
        for match in re.finditer(b'PDPHASE1', data):
            ptr, seq, capacity, pc = struct.unpack_from('>4I', data, match.start()+8)
            if ptr and 0 < capacity <= MAX_CAPACITY and capacity & (capacity-1) == 0 and pc:
                headers.append((seq, ptr, pc, origin + match.start(), capacity))
    if not headers:
        raise ValueError('No initialized PDPHASE1 header')
    # Loader file copies retain zero pointers; only the installed copy is live.
    assert len(headers) == 1, 'Ambiguous live phase header'
    seq, ptr, pc, address, capacity = headers[0]
    for origin, data in memories:
        off = ptr - origin
        if 0 <= off and off + capacity*16 <= len(data):
            return seq, pc, address, data[off:off+capacity*16], capacity
    raise ValueError('Phase ring is outside captured memory')


def records(path):
    first, pc, address, _, capacity = snapshot(path)
    last, final_pc, final_address, data, final_capacity = snapshot(path, True)
    assert (pc, address, capacity) == (final_pc, final_address, final_capacity)
    assert 0 < last-first <= capacity, 'Phase ring overwrote the capture window'
    result = []
    for sequence in range(first, last):
        seq, vbl, beam, event, ticks = struct.unpack_from('>IIIHH', data, (sequence % capacity)*16)
        assert seq == sequence, 'Incomplete phase record'
        # Beam time in 7 MHz CPU clocks. PAL non-interlaced long fields are 313
        # lines. The low horizontal bit is unavailable; resolution is 2 clocks.
        clocks = vbl*FIELD_CLOCKS + ((beam >> 8) & 511)*454 + (beam & 255)*2
        result.append(dict(sequence=seq, vbl=vbl, beam=beam, event=event,
                           ticks=ticks, clocks=clocks))
    assert all(b['clocks'] >= a['clocks'] for a, b in zip(result, result[1:])), 'VBL/beam clock went backwards'
    return pc, address, result


def frames(events, clock_key='clocks'):
    """Exclusive attribution using active nested phases; other includes hook cost."""
    totals = []
    current = defaultdict(float)
    active = []
    started = False
    previous = None
    for event in events:
        now, ident = event[clock_key], event['event']
        if previous is not None and started:
            current[PAIRS[active[-1]][0] if active else 'other'] += now-previous
        if ident == 13:
            if started:
                totals.append(dict(current))
            current = defaultdict(float)
            started = True
        # Retiring-world exits end the scheduler without committing a tick.
        # A parent end closes that abandoned step; event 15 alone counts ticks.
        if ident == 2 and active and active[-1] == 16:
            active.pop()
        if ident in PAIRS:
            if ident in active:
                raise ValueError(f'Unclosed phase {ident}')
            active.append(ident)
        elif ident in ENDS and ENDS[ident] in active:
            start = ENDS[ident]
            assert active[-1] == start, f'Out-of-order phase end {ident}: {active}'
            active.pop()
        previous = now
    return totals


def trace_times(path, pc, address, events):
    import _amigaxdev
    from amigaxdev import barto
    trace = barto.load(path / 'trace.bin')
    wanted = {(e['vbl'], e['beam'], e['event']): e for e in events}
    total = 0
    matched = set()
    for field in trace.fields:
        for at, cost, regs in trace.instructions(field):
            # The second beam read sees the first beam value in D1. Sum the
            # emulator's independent instruction costs up to that boundary.
            if at == pc+6 and regs[8] == address:
                key = (regs[0], regs[1], regs[2])
                if key in wanted:
                    wanted[key]['trace_clocks'] = total
                    matched.add(key)
            # Barto instruction units scale with the emulated CPU (M4 has
            # 284204 per field); normalize to the beam clock, not CPU MHz.
            total += cost * FIELD_CLOCKS / field.cycles
    indices = [i for i, event in enumerate(events) if 'trace_clocks' in event]
    assert indices, 'No phase samples in trace'
    first, last = indices[0], indices[-1]
    assert len(indices) == last-first+1, f'Missing interior trace records: {[e["sequence"] for e in events[first:last+1] if "trace_clocks" not in e]}'
    # Profiling begins at a field boundary after the debugger anchor and ends
    # before the final snapshot. Compare only their common contiguous window.
    return events[first:last+1], first, len(events)-1-last


def report(path, compare=False):
    pc, address, events = records(path)
    trimmed = (0, 0)
    if compare:
        events, before, after = trace_times(path, pc, address, events)
        trimmed = (before, after)
    samples = frames(events)
    assert samples, 'No complete present intervals'
    names = ['world', 'render', 'wait', 'copy', 'hud', 'timer', 'present', 'other']
    scale = 20/FIELD_CLOCKS
    result = {'frames': len(samples), 'phases_ms': {}, 'clock': 'PAL VBL + double-read beam'}
    for name in names:
        values = sorted(s.get(name, 0)*scale for s in samples)
        result['phases_ms'][name] = {'mean': statistics.mean(values),
                                   'p95': values[max(0, (95*len(values)+99)//100-1)]}
    presents = [e for e in events if e['event'] == 13]
    histogram = Counter(min(3, b['vbl']-a['vbl']) for a, b in zip(presents, presents[1:]))
    result['field_histogram'] = {str(n) if n < 3 else '3+': histogram[n] for n in (1, 2, 3)}
    result['observed_world_completion_events'] = sum(e['event'] == 15 for e in events)
    ticks = (presents[-1]['ticks']-presents[0]['ticks']) & 65535
    result['completed_world_ticks_in_frames'] = ticks
    if ticks:
        result['world_ms_per_completed_tick'] = sum(s.get('world', 0) for s in samples)*scale/ticks
    if compare:
        result['snapshot_records_outside_trace'] = dict(before=trimmed[0], after=trimmed[1])
        trace_samples = frames(events, 'trace_clocks')
        assert len(trace_samples) == len(samples)
        comparison = {}
        for name in names:
            beam = sum(s.get(name, 0) for s in samples)
            traced = sum(s.get(name, 0) for s in trace_samples)
            error = abs(beam-traced)/traced if traced else (0 if not beam else float('inf'))
            comparison[name] = dict(beam_clocks=beam, trace_clocks=traced, relative_error=error)
        result['trace_comparison'] = comparison
        if ticks:
            result['world_beam_clocks_per_tick'] = comparison['world']['trace_clocks']/ticks
        result['trace_gate_passed'] = all(v['relative_error'] <= .02 for v in comparison.values())
    return result


def handshake_report(path):
    """C1: each staged copy follows a completed wait and the next display VBL."""
    _, _, events = records(path)
    present = wait = None
    copies = []
    for event in events:
        if event['event'] == 14:
            present = event
            wait = None
        elif event['event'] == 6:
            wait = event
        elif event['event'] == 7 and present is not None:
            assert wait is not None, 'Copy without completed handshake'
            assert wait['clocks'] <= event['clocks'], 'Copy precedes wait completion'
            assert wait['vbl'] > present['vbl'], 'Copy handshake did not cross presentation VBL'
            copies.append(dict(sequence=event['sequence'],
                fields_since_present=event['vbl']-present['vbl'],
                clocks_after_wait=event['clocks']-wait['clocks']))
    assert copies, 'No staged copies with a preceding presentation'
    return dict(passed=True, checked_copies=len(copies),
                minimum_fields_since_present=min(c['fields_since_present'] for c in copies),
                minimum_clocks_after_wait=min(c['clocks_after_wait'] for c in copies))


def world_cost(path, listing):
    """B3: uninstrumented 68000 steps, entry through committed world clock."""
    import _amigaxdev
    from amigaxdev import barto
    cfg = json.loads((path/'configuration.json').read_text())
    assert cfg['CPU'] == '68000', 'B3 cost is defined for M1'
    # VASM listings include the shared include files' Latin-1 copyright text.
    source = listing.read_text(encoding='latin-1')
    symbols = {name: int(value, 16) for name, value in
               re.findall(r'^(\w+) +00:([0-9A-Fa-f]+)$', source, re.M)}
    commits = re.findall(r'^00:([0-9A-Fa-f]+) +([0-9A-Fa-f]+)\s+.*addq\.l #4,12\(a0\)', source, re.M)
    assert len(commits) == 1, 'Expected one world-clock commit instruction'
    committed = int(commits[0][0], 16) + len(commits[0][1])//2
    game = int((path/'game-base.txt').read_text(), 0)
    chip = (path/'chip.bin').read_bytes()
    assert struct.unpack_from('>H', chip, game+0xca44)[0] == 0x4ef9
    live = struct.unpack_from('>I', chip, game+0xca46)[0]-symbols['timing_frame']
    assert struct.unpack_from('>I', chip, game+0xcede)[0] == live+symbols['timing_world_end'], 'Listing/build mismatch'
    start_pc = live+symbols['timing_world_begin']
    end_pc = live+committed
    trace = barto.load(path/'trace.bin')
    elapsed = 0
    start = None
    costs = []
    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            if pc == start_pc:
                assert start is None, 'World step restarted before committing'
                start = elapsed
            elif pc == end_pc and start is not None:
                costs.append(elapsed-start)
                start = None
            elapsed += cost
    assert costs, 'No complete world steps in trace'
    costs.sort()
    return dict(instrument='uninstrumented 68000 instruction trace', completed_steps=len(costs),
                cycles_per_step_mean=statistics.mean(costs),
                cycles_per_step_p95=costs[max(0, (95*len(costs)+99)//100-1)],
                cycles_per_step_min=min(costs), cycles_per_step_max=max(costs),
                includes_interrupts=True,
                boundary='timing_world_begin through committed +4 world-clock update',
                excludes='frame allocator, rendering/HUD-owned work, and post-commit loop/restore tail')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--trace', action='store_true')
    parser.add_argument('--handshake', action='store_true', help='C1 staged-copy/handshake ordering gate')
    parser.add_argument('--world-listing', type=Path, help='B3: matching uninstrumented full-verify assembler listing')
    args = parser.parse_args()
    result = (world_cost(args.capture, args.world_listing) if args.world_listing else
              handshake_report(args.capture) if args.handshake else report(args.capture, args.trace))
    print(json.dumps(result, indent=2))
    if args.trace and not result['trace_gate_passed']:
        raise SystemExit('Phase/trace 2% gate failed')
