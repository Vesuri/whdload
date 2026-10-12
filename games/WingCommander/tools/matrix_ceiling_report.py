#!/usr/bin/env python3
"""Check matched VERIFY c2p fixtures and compare the complete intro window."""
import argparse
import hashlib
import json
from pathlib import Path
from matrix_scene_report import report as scene_report

ORIGINAL = '5fbbb774bba3c794a776acc25f33c3f47c579449e1ba1a21c31418716aa74986'
ENTRIES = (0x17f6, 0x195e, 0x1ac6)


def compare(control, candidate):
    runs = (control, candidate)
    metadata = [json.loads((run/'result.json').read_text()) for run in runs]
    reports = [scene_report(run) for run in runs]
    left, right = metadata
    if (left.get('ceiling'), right.get('ceiling')) != ('control', 'c2p'):
        raise ValueError('explicit control and c2p arms required')
    for key in ('machine', 'nommu_core', 'mmu_core', 'options', 'audit_cacr',
                'emulator_sha256', 'hunks', 'slave', 'boot_cpu', 'live_cpu',
                'profiles', 'raw_chunky', 'host_warp', 'dma', 'names'):
        if left.get(key) != right.get(key):
            raise ValueError('unmatched configuration: '+key)
    binaries = []
    for run, meta in zip(runs, metadata):
        paths = list((run/'run').glob('boot.*/dh1/WingCommanderCD32/WingCommanderCD32.Slave'))
        if len(paths) != 1:
            raise ValueError('one retained boot slave required')
        data = paths[0].read_bytes()
        if len(data) != 7728 or hashlib.sha256(data).hexdigest() != meta['slave_sha256']:
            raise ValueError('retained fixture hash/size mismatch')
        binaries.append(data)
        memory = (run/'fast.bin').read_bytes()
        for offset in ENTRIES:
            at = meta['slave']-0x200000+offset
            if memory[at:at+2] != data[32+offset:34+offset]:
                raise ValueError('live converter entry differs from fixture')
    if left['slave_sha256'] != ORIGINAL:
        raise ValueError('control must be the pinned original slave')
    expected = bytearray(binaries[0])
    for offset in ENTRIES:
        expected[32+offset:34+offset] = bytes.fromhex('4e75')
    if binaries[1] != expected:
        raise ValueError('unexpected fixture differences')
    scenes = []
    for a, b in zip(reports[0]['scenes'][2:33], reports[1]['scenes'][2:33]):
        scenes.append(dict(scene=a['scene'], control=a, bypass=b,
                           seconds_saved=a['seconds']-b['seconds'],
                           publication_rate_ratio=b['publication_hz']/a['publication_hz']
                           if a['publication_hz'] else None))
    totals = {}
    for arm in ('control', 'bypass'):
        seconds = sum(s[arm]['seconds'] for s in scenes)
        publications = sum(s[arm]['publications'] for s in scenes)
        totals[arm] = dict(seconds=seconds, publications=publications,
                           publication_hz=publications/seconds)
    totals['seconds_saved'] = totals['control']['seconds']-totals['bypass']['seconds']
    totals['publication_rate_ratio'] = totals['bypass']['publication_hz']/totals['control']['publication_hz']
    return dict(matched_c2p_fixture_pass=True, live_entry_checks=6,
                window='origin-load entry through cycle-complete entry',
                totals=totals, scenes=scenes,
                limitations=['The original limiter remains active.',
                             'Bypassed conversion intentionally invalidates planar output.',
                             'A single matched pair does not establish variability or physical CPU performance.',
                             'This comparison does not complete the phase 4 matrix gate.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.control, args.candidate), indent=2))
