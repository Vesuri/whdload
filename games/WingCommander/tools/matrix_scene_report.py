#!/usr/bin/env python3
"""Validate scene counters independently of instruction-profiler availability."""
import argparse
import collections
import json
import re
from pathlib import Path
from intro_capture import SCENES


def report(run, *, allow_diagnostic=False):
    meta = json.loads((run/'result.json').read_text())
    if not meta['complete'] or (meta.get('diagnostic_stops') and not allow_diagnostic):
        raise ValueError('complete uninterrupted scene capture required')
    cpu = dict(re.findall(r'(\w+)=(\w+)', meta['boot_cpu']))
    models = {'a1200-fast': '68020', 'a1200-030': '68030',
              'a1200-040': '68040', 'a1200-060': '68060'}
    if cpu.get('model') != models[meta['machine']] or cpu.get('mmu') != ('68030' if meta.get('mmu_core') else '0'):
        raise ValueError('unexpected counter interpreter')
    if cpu.get('exact') != '1' or cpu.get('memory_exact') != '1':
        raise ValueError('cycle-exact configuration required')
    if meta['machine'] != 'a1200-fast' and not (meta.get('nommu_core') or meta.get('mmu_core')):
        raise ValueError('accelerated counter capture needs an explicit core')
    if meta.get('mmu_core') and meta['machine']!='a1200-030':
        raise ValueError('only the 030 MMU counter interpreter is covered')
    if meta.get('mmu_core'):
        live=dict(re.findall(r'(\w+)=(\w+)',meta['live_cpu']))
        if 'tc030' not in live:raise ValueError('actual MMU translation state missing')
        enabled=bool(int(live['tc030'],16)&0x80000000)
        options=meta['options'].upper().split()
        if ('MMU' in options and not enabled) or ('NOMMU' in options and enabled):
            raise ValueError('actual translation state disagrees with requested option')
    for key in ('boot_cpu', 'live_cpu'):
        actual = dict(re.findall(r'(\w+)=(\w+)', meta[key]))
        if meta.get('instant_blitter') or 'immediate_blits' in actual:
            if actual.get('immediate_blits') != ('1' if meta.get('instant_blitter') else '0'):
                raise ValueError('instant-blitter state disagrees with capture arm')
    h = meta['hunks']
    cuts = [0xf800d2, h[3]]+[h[n]+pc for n, pc, _ in SCENES]
    cuts += [h[0]+0x1fdd6]*18+[h[0]+0x1fe48, h[0]+0x20214]
    if len(cuts) != 35 or len(meta['names']) != 35:
        raise ValueError('unexpected scene schema')
    boundaries = []
    publications = collections.Counter()
    changes = collections.defaultdict(list)
    current = -1
    last_time = -1
    last_field = -1
    for line in (run/'matrix-events.txt').read_text().splitlines():
        p = line.split()
        kind, scene = p[0], int(p[1])
        if kind == 'B':
            if len(p) != 6 or scene != current+1 or scene >= len(cuts):
                raise ValueError('missing/reordered scene boundary')
            if int(p[2], 16) != cuts[scene]:
                raise ValueError('scene boundary PC mismatch')
            field, cycles, cacr = int(p[3]), int(p[4]), int(p[5], 16)
            current = scene
            boundaries.append((scene, field, cycles))
        elif kind in ('P', 'C'):
            if scene != current or not 0 <= scene < 34:
                raise ValueError('event outside its current scene')
            if len(p) != (5 if kind == 'P' else 9):
                raise ValueError('malformed event')
            field, cycles, cacr = int(p[2]), int(p[3]), int(p[-1], 16)
            if kind == 'P':
                publications[scene] += 1
            else:
                size, paired, changed, blocks = map(int, p[4:8])
                if size not in (40960, 53120, 64000) or paired not in (0, 1):
                    raise ValueError('invalid census geometry')
                if not 0 <= blocks <= size//32 or not blocks <= changed <= min(size, blocks*32):
                    raise ValueError('invalid change counts')
                if not paired and (changed or blocks):
                    raise ValueError('unpaired frame has changes')
                changes[scene].append((size, paired, changed, blocks))
        else:
            raise ValueError('unknown event')
        if cycles < last_time or field < last_field:
            raise ValueError('nonmonotonic event clock')
        if current > 0 and cacr != meta['audit_cacr']:
            raise ValueError('cache audit mismatch')
        last_time, last_field = cycles, field
    if len(boundaries) != 35:
        raise ValueError('incomplete scene ledger')
    scenes = []
    for a, b in zip(boundaries, boundaries[1:]):
        index, field, cycles = a
        units = b[2]-cycles
        if units <= 0:
            raise ValueError('empty scene interval')
        # The fixed capture harness requests PAL. get_cycles uses 512 units
        # per 3,546,895 Hz colour clock, independently of CPU clock scaling.
        seconds = units/(512*3546895)
        pairs = [c for c in changes[index] if c[1]]
        compared = sum(c[0] for c in pairs)
        scenes.append(dict(scene=meta['names'][index], units=units,
                           fields=b[1]-field, seconds=seconds,
                           publications=publications[index], publication_hz=publications[index]/seconds,
                           c2p_calls=len(changes[index]), compared_frames=len(pairs),
                           compared_bytes=compared, changed_bytes=sum(c[2] for c in pairs),
                           changed_32byte_blocks=sum(c[3] for c in pairs)))
    return dict(scene_ledger_pass=True, validated_timing_baseline=False,
                diagnostic_capture=bool(meta.get("diagnostic_stops")),
                cpu_clock_validated=meta.get('clock_validated', meta['machine']=='a1200-fast'),
                machine=meta['machine'], options=meta['options'], scenes=scenes,
                limitations=['Ledger structure is checked; repeatability and independent observer checks are separate.',
                             'Emulated PAL durations do not calibrate the requested CPU MHz.',
                             'No instruction, DMA, interrupt or idle costs are inferred from these counters.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    print(json.dumps(report(args.run), indent=2))
