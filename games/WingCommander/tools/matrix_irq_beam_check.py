#!/usr/bin/env python3
"""Check callback elapsed intervals against read-only PAL beam observations."""
import argparse
import json
from pathlib import Path
from matrix_irq_check import check as scope_check, NAMES, OFFSETS
from matrix_irq_trace_check import compare_control


def position(beam):
    # Same UAE VHPOSR convention validated by Stellar 7's presentation observer.
    lines = 312 + ((beam >> 31) & 1)
    y, x = (beam >> 8) & 511, beam & 255
    if beam & (1 << 23) or y >= lines or x >= 228:
        raise ValueError('unexpected PAL beam geometry')
    if x == 1:
        y += 1
        x = 0
    elif x == 0:
        x = 226
    else:
        x -= 1
    return (y*227+x) % (lines*227), lines*227


def check(run):
    scope_check(run, allow_diagnostic=True)
    meta = json.loads((run/'result.json').read_text())
    if not meta.get('irq_beam') or not meta.get('diagnostic_stops'):
        raise ValueError('explicit diagnostic beam capture required')
    # In this pinned build, m68k_run_3ce services debugger stops inside
    # do_specialties, then may advance one CYCLE_UNIT for cached instructions
    # before the next wc_matrix_observe. Each beam endpoint can therefore
    # precede its ledger endpoint by 0 or 512 units. This is separate from
    # beam quantisation; do not infer it from the observed residual.
    endpoint_skew = 0
    if meta['machine'] in ('a1200-040', 'a1200-060'):
        if meta['emulator_sha256'] != 'c30ad609dc1141b47d3b9cfbf7d5a86666445fee7985907beef60b095679d940':
            raise ValueError('unreviewed 040/060 debugger endpoint ordering')
        endpoint_skew = 512
    samples = json.loads((run/'irq-beam.json').read_text())
    if [sample['kind'] for sample in samples] != [0]*3+[1]*3+[2]*3:
        raise ValueError('expected three consecutive observations of each callback')
    entries, returns = [], {}
    credits = None
    for line in (run/'irq-events.txt').read_text().splitlines():
        p = line.split()
        if p[:2] == ['B', '15']:
            credits = int(p[2])
        elif p[0] == 'E':
            entries.append(dict(serial=int(p[1]),kind=int(p[2]),at=int(p[3]),
                                pc=int(p[4],16),sp=int(p[5],16),ret=int(p[6],16)))
        elif p[0] == 'R':
            returns[int(p[1])] = int(p[2])
    if credits is None:
        raise ValueError('credits anchor absent')
    after = credits
    last_serial = 0
    rows = []
    for sample in samples:
        kind, begin, end = sample['kind'], sample['begin'], sample['end']
        # Each GDB continue selects the first matching entry after the previous
        # observed return. Match by order/PC/stack, never by elapsed duration.
        entry = next((e for e in entries if e['at'] >= after and e['serial'] > last_serial and e['kind'] == kind), None)
        if entry is None:
            raise ValueError('beam observation lacks a callback entry')
        if begin['pc'] != meta['hunks'][0]+OFFSETS[kind] or any(begin[k] != entry[k] for k in ('pc','sp','ret')):
            raise ValueError('beam observation entry/stack differs from scope ledger')
        if end['pc'] != entry['ret'] or end['sp'] != entry['sp']+4:
            raise ValueError('beam observation return differs from scope ledger')
        finish = returns[entry['serial']]
        elapsed = finish-entry['at']
        start, length = position(begin['beam'])
        stop, end_length = position(end['beam'])
        if not 0 <= elapsed < length*512:
            raise ValueError('beam interval can span a full field; ambiguous wrap')
        if stop >= start and length != end_length:
            raise ValueError('field geometry changed without a beam wrap')
        clocks = stop-start if stop >= start else length-start+stop
        residual = elapsed-clocks*512
        if abs(residual) >= 512 + endpoint_skew:
            raise ValueError('callback duration exceeds beam quantisation and endpoint-skew bounds')
        rows.append(dict(callback=NAMES[kind],serial=entry['serial'],elapsed_units=elapsed,
                         beam_clocks=clocks,residual_units=residual))
        after = finish
        last_serial = entry['serial']
    return dict(independent_beam_duration_pass=True, calls=len(rows),rows=rows,
                maximum_absolute_residual_units=max(abs(r['residual_units']) for r in rows),
                resolution_units=512, debugger_endpoint_skew_units=endpoint_skew,
                residual_bound_exclusive_units=512+endpoint_skew,
                scope='Nine complete callbacks at credits entry; inclusive emulated elapsed time.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    parser.add_argument('--control',type=Path)
    args=parser.parse_args()
    result=check(args.run)
    if args.control:result['control_comparison']=compare_control(args.run,args.control)
    print(json.dumps(result,indent=2))
