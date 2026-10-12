#!/usr/bin/env python3
"""Cross-check callback intervals against independently recorded Barto instructions."""
import argparse
import json
import hashlib
import re
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from matrix_irq_check import check as scope_check, OFFSETS, NAMES


def check(run):
    scope_check(run, allow_diagnostic=True)
    meta = json.loads((run/'result.json').read_text())
    if not meta.get('irq_trace') or not meta.get('diagnostic_stops'):
        raise ValueError('explicit diagnostic IRQ trace required')
    cpu = dict(re.findall(r'(\w+)=(\w+)', meta['boot_cpu']))
    if cpu.get('model') != '68020' or cpu.get('unit') != '128':
        raise ValueError('cross-check currently covers stock-clock 020 only')
    unit = int(cpu['unit'])
    trace = barto.load(str(run/'irq-trace.bin'))
    starts, ends, entries, returns = {}, {}, [], {}
    for line in (run/'irq-events.txt').read_text().splitlines():
        p = line.split()
        if p[0] == 'F':
            state, index, at = map(int, p[1:])
            target = starts if state == 0 else ends
            if index in target:
                raise ValueError('duplicate trace field boundary')
            target[index] = at
        elif p[0] == 'E':
            entries.append(dict(serial=int(p[1]), kind=int(p[2]), at=int(p[3]),
                                pc=int(p[4],16), sp=int(p[5],16), ret=int(p[6],16)))
        elif p[0] == 'R':
            returns[int(p[1])] = int(p[2])
    if sorted(starts) != list(range(len(trace.fields))) or starts.keys() != ends.keys():
        raise ValueError('trace field anchors missing')
    fast = (run/'fast.bin').read_bytes()
    def opcode(pc):
        if 0x200000 <= pc < 0xa00000:
            data, offset = fast, pc-0x200000
        elif 0xf80000 <= pc < 0x1000000:
            data, offset = trace.rom, pc-0xf80000
        else:
            data, offset = trace.chip, pc
        if not 0 <= offset < len(data)-1:
            raise ValueError('return opcode outside captured memory')
        return int.from_bytes(data[offset:offset+2], 'big')
    targets = [meta['hunks'][0]+offset for offset in OFFSETS]
    rows = []
    for field in trace.fields:
        start, end = starts[field.index], ends[field.index]
        if end <= start or field.cycles != end//unit-start//unit:
            raise ValueError('trace field clock disagrees with independent anchors')
        records = list(trace.instructions(field))
        observed = [(i, pc, regs[15]) for i, (pc, _, regs) in enumerate(records) if pc in targets]
        expected = [e for e in entries if start <= e['at'] < end]
        if [(pc, sp) for _, pc, sp in observed] != [(e['pc'], e['sp']) for e in expected]:
            raise ValueError('trace field callback entries disagree with scope ledger')
        for (index, _, _), entry in zip(observed, expected):
            finish = returns[entry['serial']]
            if finish >= end:
                continue  # A partial interval at a field edge is not a whole-call check.
            stop = None
            for j in range(index+1, len(records)):
                pc, _, regs = records[j]
                if pc == entry['ret'] and regs[15] == entry['sp']+4:
                    stop = j
                    break
            if stop is None:
                raise ValueError('complete callback return absent from trace')
            previous = next((pc for pc, _, _ in reversed(records[index:stop])
                             if pc not in (None, 0x7fffffff)), None)
            if previous is None or opcode(previous) != 0x4e75:
                raise ValueError('callback does not return through a traced RTS')
            selected = records[index:stop]
            if any(pc is None for pc, _, _ in selected):
                raise ValueError('callback contains unrecorded instruction context')
            measured = finish-entry['at']
            trace_units = sum(cost for _, cost, _ in selected)*unit
            residual = measured-trace_units
            # Barto floors each instruction/gap independently to CPU cycles.
            bound = len(selected)*(unit-1)
            if not 0 <= residual <= bound:
                raise ValueError('callback duration outside trace quantisation bound')
            # This pinned 020 fixture reconciles without any rounding loss.
            # Do not use a broad rounding bound to accept changed measurements.
            if residual != 0:
                raise ValueError('callback duration differs from exact 020 trace fixture')
            rows.append(dict(field=field.index, callback=NAMES[entry['kind']],
                             serial=entry['serial'], elapsed_units=measured,
                             trace_units=trace_units, residual_units=residual,
                             quantisation_bound_units=bound, records=len(selected)))
    if set(row['callback'] for row in rows) != set(NAMES):
        raise ValueError('not all three callbacks have complete traced calls')
    return dict(independent_duration_exact_pass=True, calls=len(rows), fields=len(trace.fields),
                maximum_residual_units=max(row['residual_units'] for row in rows),
                maximum_residual_fraction=max(row['residual_units']/row['elapsed_units'] for row in rows),
                rows=rows, scope='Complete calls in a diagnostic five-field 020 window; includes callees and preemption.')


def compare_control(run, control):
    from PIL import Image
    scope_check(control)
    left = json.loads((control/'result.json').read_text())
    right = json.loads((run/'result.json').read_text())
    if left.get('diagnostic_stops') or not right.get('irq_trace'):
        raise ValueError('uninterrupted scope control and diagnostic trace required')
    for key in ('machine', 'options', 'audit_cacr', 'hunks', 'slave', 'slave_sha256',
                'boot_cpu', 'live_cpu', 'nommu_core', 'mmu_core', 'raw_chunky',
                'profiles', 'idle', 'dma', 'host_warp', 'irq_scopes'):
        if left.get(key) != right.get(key):
            raise ValueError('unmatched diagnostic trace configuration: '+key)
    if (run/'matrix-events.txt').read_bytes() != (control/'matrix-events.txt').read_bytes():
        raise ValueError('diagnostic trace changed publication/census ledger')
    scopes = [(p/'irq-events.txt').read_text().splitlines() for p in (control, run)]
    if scopes[0] != [line for line in scopes[1] if not line.startswith('F ')]:
        raise ValueError('diagnostic trace changed callback intervals')
    a, b = [(p/'fast.bin').read_bytes() for p in (control, run)]
    for base, size in zip(left['hunks'], (0x35ea4, 0xfda0, 4, 0x1590)):
        offset = base-0x200000
        if a[offset:offset+size] != b[offset:offset+size]:
            raise ValueError('diagnostic trace changed game hunk')
    if not left.get('raw_chunky'):
        raise ValueError('raw source controls required')
    def digest(path):
        h = hashlib.sha256()
        with path.open('rb') as file:
            for data in iter(lambda: file.read(1024*1024), b''):
                h.update(data)
        return h.digest()
    if digest(control/'chunky-sources.bin') != digest(run/'chunky-sources.bin'):
        raise ValueError('diagnostic trace changed raw source buffers')
    with Image.open(control/'menu.png') as a, Image.open(run/'menu.png') as b:
        if a.size != b.size or a.convert('RGB').tobytes() != b.convert('RGB').tobytes():
            raise ValueError('diagnostic trace changed menu image')
    return dict(diagnostic_execution_matches_control=True, all_callback_intervals_identical=True,
                emulator_hashes=[left['emulator_sha256'], right['emulator_sha256']],
                scope='Explicit cross-build trace validation; not a same-binary recording-off control.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--control', type=Path)
    args = parser.parse_args()
    result = check(args.run)
    if args.control:
        result['control_comparison'] = compare_control(args.run, args.control)
    print(json.dumps(result, indent=2))
