#!/usr/bin/env python3
"""Check complete game VBL callback intervals without claiming CPU self cost."""
import argparse
import json
import re
from pathlib import Path
from matrix_scene_report import report as scene_report

CLOCK = 512*3546895
OFFSETS = (0x34162, 0x27810, 0x33e62)
NAMES = ('game-vbl', 'music-vbl', 'joypad-vbl')


def integrate(lines, cuts, h0):
    scene = -1
    last = None
    serial = 0
    stack = []
    rows = []
    for line in lines:
        p = line.split()
        if not p or p[0] not in ('B', 'E', 'R', 'F'):
            raise ValueError('unknown IRQ record')
        expected = {'B': 3, 'E': 7, 'R': 5, 'F': 4}[p[0]]
        if len(p) != expected:
            raise ValueError('malformed IRQ record')
        at = int(p[3] if p[0] in ('E', 'F') else p[2])
        if at < 0 or (last is not None and at < last):
            raise ValueError('nonmonotonic IRQ clock')
        if last is not None:
            if not 0 <= scene < len(cuts)-1:
                raise ValueError('IRQ event outside measured window')
            elapsed = at-last
            for entry in stack:
                rows[scene]['inclusive_units'][entry[1]] += elapsed
            if stack:
                rows[scene]['callback_union_units'] += elapsed
                rows[scene]['innermost_selected_callback_units'][stack[-1][1]] += elapsed
        if p[0] == 'B':
            index = int(p[1])
            if index != scene+1 or index >= len(cuts) or cuts[index] != (index, at):
                raise ValueError('IRQ scene boundary differs from publication ledger')
            scene = index
            if index < len(cuts)-1:
                rows.append(dict(inclusive_units=[0]*3, innermost_selected_callback_units=[0]*3,
                                 callback_union_units=0, entries=[0]*3, returns=[0]*3))
        elif p[0] == 'F':
            if int(p[1]) not in (0, 1) or int(p[2]) < 0:
                raise ValueError('invalid trace boundary')
        elif p[0] == 'E':
            number, kind = map(int, p[1:3])
            pc, sp, ret = (int(v, 16) for v in p[4:])
            if not 0 <= scene < len(cuts)-1 or number != serial+1 or not 0 <= kind < 3:
                raise ValueError('invalid IRQ entry sequence')
            if pc != h0+OFFSETS[kind] or sp & 1 or not 0x100 <= sp <= 0x9ffffc or ret & 1:
                raise ValueError('invalid IRQ entry address/stack')
            serial = number
            stack.append((number, kind, sp, ret))
            if len(stack) > 16:
                raise ValueError('IRQ nesting overflow')
            rows[scene]['entries'][kind] += 1
        else:
            number = int(p[1])
            pc, sp = (int(v, 16) for v in p[3:])
            if not stack or stack[-1][0] != number:
                raise ValueError('unmatched IRQ return')
            _, kind, entry_sp, ret = stack.pop()
            if pc != ret or sp != entry_sp+4:
                raise ValueError('IRQ return does not restore saved stack slot')
            rows[scene]['returns'][kind] += 1
        last = at
    if scene != len(cuts)-1 or stack or len(rows) != len(cuts)-1:
        raise ValueError('incomplete IRQ scope coverage')
    for i, row in enumerate(rows):
        units = cuts[i+1][1]-cuts[i][1]
        if not 0 <= row['callback_union_units'] <= units:
            raise ValueError('IRQ callback union exceeds scene')
        if sum(row['innermost_selected_callback_units']) != row['callback_union_units']:
            raise ValueError('IRQ scope partition disagrees')
    return rows


def check(run, *, allow_diagnostic=False):
    meta = json.loads((run/'result.json').read_text())
    if not meta.get('irq_scopes'):
        raise ValueError('IRQ scope-enabled capture required')
    scenes = scene_report(run, allow_diagnostic=allow_diagnostic)['scenes']
    cuts = []
    for line in (run/'matrix-events.txt').read_text().splitlines():
        p = line.split()
        if p[0] == 'B':
            cuts.append((int(p[1]), int(p[4])))
    rows = integrate((run/'irq-events.txt').read_text().splitlines(), cuts, meta['hunks'][0])
    for row, scene in zip(rows, scenes):
        row.update(scene=scene['scene'], scene_units=scene['units'],
                   callback_union_seconds=row['callback_union_units']/CLOCK)
    return dict(callback_scope_accounting_pass=True, callback_names=NAMES,
                callback_hunk_offsets=OFFSETS, scenes=rows, validated_baseline=False,
                limitations=['Elapsed callback time includes callees and preemption.',
                             'Innermost selected scope time is not routine self time.',
                             'Exception entry, dispatcher and other handlers are outside these scopes.',
                             'Independent trace validation and recording-off neutrality are required.'])


def compare_profile(run, profile):
    from matrix_report import report as profile_report, read_aprof
    measured = check(run)
    profile_report(profile)
    left = json.loads((run/'result.json').read_text())
    right = json.loads((profile/'result.json').read_text())
    for key in ('machine', 'options', 'audit_cacr', 'hunks', 'slave', 'slave_sha256'):
        if left[key] != right[key]:
            raise ValueError('unmatched IRQ profile: '+key)
    for field in ('boot_cpu', 'live_cpu'):
        a = dict(re.findall(r'(\w+)=(\w+)', left[field]))
        b = dict(re.findall(r'(\w+)=(\w+)', right[field]))
        # Older validated profiles predate the extra TC/immediate-blit fields.
        # Require every original effective CPU setting, plus identical execution.
        for key in ('model', 'mmu', 'exact', 'memory_exact', 'blitter_exact',
                    'multiplier', 'frequency', 'unit', 'cacr'):
            if key not in a or key not in b or a[key] != b[key]:
                raise ValueError('unmatched IRQ profile CPU setting: '+key)
    if (run/'matrix-events.txt').read_bytes() != (profile/'matrix-events.txt').read_bytes():
        raise ValueError('IRQ profile must have identical scene/publication/census ledger')
    pcs = [left['hunks'][0]+offset for offset in OFFSETS]
    for i, scene in enumerate(measured['scenes']):
        if i == 0:
            continue  # The game is not loaded throughout reset.
        header, records, _, _, _ = read_aprof(profile/f'scene-{i:02d}.aprof')
        if header.get('source_pc_stable') != 1:
            raise ValueError('stable executing-PC profile required')
        counts = [sum(record[2] for record in records if record[0] == pc) for pc in pcs]
        if counts != scene['entries']:
            raise ValueError('independent IRQ entry instruction counts disagree')
    return dict(independent_entry_counts_pass=True,
                scope='Checks callback entry counts, not complete-call elapsed costs.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--profile-control', type=Path)
    args = parser.parse_args()
    result = check(args.run)
    if args.profile_control:
        result['profile_crosscheck'] = compare_profile(args.run, args.profile_control)
    print(json.dumps(result, indent=2))
