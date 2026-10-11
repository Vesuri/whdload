#!/usr/bin/env python3
"""Measure observed SIM60 update/presentation gaps at display-field resolution.

Only intervals with both endpoints in the trace are complete. Boundary tails
are lower bounds, never maximum-latency claims for the game as a whole.
"""
import argparse
import json
import re
import struct
from pathlib import Path
import barto
from sim60_state import read
from stellar7_report import locate


def summarize(fields, total_fields, hz):
    gaps = [b-a for a, b in zip(fields, fields[1:])]
    return dict(events=len(fields), event_fields=fields,
                complete_gap_fields=gaps,
                largest_complete_gap_fields=max(gaps, default=None),
                # Endpoints can occur anywhere within their respective fields.
                largest_complete_gap_seconds_bounds=(
                    [max(0, max(gaps)-1)/hz, (max(gaps)+1)/hz] if gaps else None),
                leading_unobserved_gap_at_least_fields=(fields[0] if fields else total_fields),
                trailing_unobserved_gap_at_least_fields=(
                    total_fields-fields[-1]-1 if fields else total_fields))


def inspect(folder, listing):
    folder, listing = Path(folder), Path(listing)
    binary = (folder/'slave.slave').read_bytes()
    assert binary == listing.with_suffix('.slave').read_bytes(), 'listing build mismatch'
    symbols = listing.read_text(encoding='latin1')
    offsets = {name: int(re.search(r'^'+name+r'\s+00:([0-9A-F]+)', symbols, re.M)[1], 16)
               for name in ('s60_update', 's60_render', 's60_loop_poll')}
    delay_match = re.search(r'^s60_loop_delay\s+00:([0-9A-F]+)', symbols, re.M)
    delay_offset = int(delay_match[1], 16) if delay_match else None
    meta = {k: int(v, 0) for k, v in re.findall(
        r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    size = struct.unpack_from('>I', binary, 28)[0]*4
    base = locate((folder/'code.bin').read_bytes(), binary[32:32+size],
                  meta['base'], header=32)
    assert base is not None, 'retained slave not found'
    trace = barto.load(folder/'trace.bin')
    hz = read(folder)['field_hz']
    assert hz in (50, 60)
    targets = {base+offsets['s60_update']: 'updates',
               meta['code']+0x6a0a: 'presentations'}
    events = {name: [] for name in targets.values()}
    render_start = None
    spans = []
    delay_start = None
    delay_spans = []
    for field in trace.fields:
        for pc, cost, regs in trace.instructions(field):
            if pc in targets:
                events[targets[pc]].append(field.index)
            if delay_offset is not None and pc == base+delay_offset and delay_start is None:
                delay_start = field.index
            if pc == base+offsets['s60_render']:
                if delay_start is not None:
                    delay_spans.append(field.index-delay_start)
                    delay_start = None
                assert render_start is None, 'overlapping render phases'
                render_start = field.index
            elif pc == base+offsets['s60_loop_poll'] and render_start is not None:
                spans.append(field.index-render_start)
                render_start = None
    return dict(fields=len(trace.fields), field_hz=hz,
                **{name: summarize(values, len(trace.fields), hz)
                   for name, values in events.items()},
                complete_render_phase_fields=spans,
                complete_injected_delay_fields=delay_spans,
                injected_delay_present=delay_offset is not None,
                incomplete_injected_delay_at_end=delay_start is not None,
                incomplete_render_at_end=render_start is not None,
                scope='Observed trace only; field differences have less than one field of endpoint uncertainty. Render spans exclude any separately reported injected delay. Update-entry gaps include simulation work, rendering and injected delay; they are not direct input-to-display measurements.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--listing', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture, args.listing), indent=2))
