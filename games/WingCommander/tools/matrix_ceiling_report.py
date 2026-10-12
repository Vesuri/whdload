#!/usr/bin/env python3
"""Check matched VERIFY rendering-ceiling fixtures and compare the complete intro window."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from PIL import Image
from matrix_scene_report import report as scene_report

ORIGINAL = '5fbbb774bba3c794a776acc25f33c3f47c579449e1ba1a21c31418716aa74986'
ENTRIES = (0x17f6, 0x195e, 0x1ac6)


def compare(control, candidate):
    runs = (control, candidate)
    metadata = [json.loads((run/'result.json').read_text()) for run in runs]
    reports = [scene_report(run) for run in runs]
    left, right = metadata
    instant = right.get('instant_blitter', False)
    drawing = right.get('ceiling') in ('drawing','drawing-bitmap','drawing-clear')
    if left.get('instant_blitter', False):
        raise ValueError('control must use normal blitter timing')
    expected_arms = ('drawing-control',right['ceiling']) if drawing else ('control','control' if instant else 'c2p')
    if instant and drawing:raise ValueError('one intervention per experiment required')
    if (left.get('ceiling'), right.get('ceiling')) != expected_arms:
        raise ValueError('explicit matched ceiling arms required')
    for key in ('boot_cpu', 'live_cpu'):
        a, b = [dict(re.findall(r'(\w+)=(\w+)', meta[key])) for meta in metadata]
        if instant:
            if a.pop('immediate_blits', None) != '0' or b.pop('immediate_blits', None) != '1':
                raise ValueError('effective instant-blitter intervention missing')
        if a != b:
            raise ValueError('unmatched CPU settings: '+key)
    for key in ('machine', 'nommu_core', 'mmu_core', 'options', 'audit_cacr',
                'emulator_sha256', 'hunks', 'slave',
                'profiles', 'raw_chunky', 'host_warp', 'dma', 'idle', 'irq_scopes', 'names'):
        if left.get(key) != right.get(key):
            raise ValueError('unmatched configuration: '+key)
    binaries = []
    for run, meta in zip(runs, metadata):
        paths = list((run/'run').glob('boot.*/dh1/WingCommanderCD32/WingCommanderCD32.Slave'))
        if len(paths) != 1:
            raise ValueError('one retained boot slave required')
        data = paths[0].read_bytes()
        if len(data) != (7836 if drawing else 7728) or hashlib.sha256(data).hexdigest() != meta['slave_sha256']:
            raise ValueError('retained fixture hash/size mismatch')
        binaries.append(data)
        memory = (run/'fast.bin').read_bytes()
        for offset in ENTRIES:
            at = meta['slave']-0x200000+offset
            if memory[at:at+2] != data[32+offset:34+offset]:
                raise ValueError('live converter entry differs from fixture')
    expected = bytearray(binaries[0])
    if drawing:
        from cd32_runtime import ROOT
        original = (ROOT/'tmp/originals/cd32/WingCommanderCD32/WingCommanderCD32.Slave').read_bytes()
        if hashlib.sha256(original).hexdigest()!=ORIGINAL:
            raise ValueError('pinned original needed to check drawing control')
        code=bytearray(original[32:-4])
        code[0x14da:0x14de]=struct.pack('>Hh',0x6100,len(code)-(0x14da+2))
        if binaries[0][32:32+len(code)]!=code:
            raise ValueError('drawing control changed original code outside the detour')
        if binaries[0][32+0x1e74:36+0x1e74]!=bytes.fromhex('48e748e7'):
            raise ValueError('drawing control does not retain original entry opcode')
        words=('4e75' if right['ceiling'] in ('drawing','drawing-bitmap') else '48e7')+('4e75' if right['ceiling'] in ('drawing','drawing-clear') else '48e7')
        expected[32+0x1e74:36+0x1e74]=bytes.fromhex(words)
        for run,meta in zip(runs,metadata):
            memory=(run/'fast.bin').read_bytes()
            marker=meta['slave']-0x200000+0x1e70
            if memory[marker:marker+4]!=struct.pack('>I',1):
                raise ValueError('drawing fixture must install exactly once')
            for index,offset in enumerate((0x2efe8,0x31cd6)):
                active=meta['ceiling']=='drawing' or meta['ceiling']==('drawing-bitmap' if index==0 else 'drawing-clear')
                word=bytes.fromhex('4e75' if active else '48e7')
                at=meta['hunks'][0]-0x200000+offset
                if memory[at:at+2]!=word:
                    raise ValueError('drawing entry does not match requested arm')
    else:
        if left['slave_sha256'] != ORIGINAL:
            raise ValueError('control must be the pinned original slave')
        if not instant:
            for offset in ENTRIES:
                expected[32+offset:34+offset] = bytes.fromhex('4e75')
    if binaries[1] != expected:
        raise ValueError('unexpected fixture differences')
    memory_a, memory_b = [(run/'fast.bin').read_bytes() for run in runs]
    final_hunks_equal = []
    for base, size in zip(left['hunks'], (0x35ea4, 0xfda0, 4, 0x1590)):
        at = base-0x200000
        final_hunks_equal.append(memory_a[at:at+size] == memory_b[at:at+size])
    with Image.open(control/'menu.png') as a, Image.open(candidate/'menu.png') as b:
        menu_equal = a.size == b.size and a.convert('RGB').tobytes() == b.convert('RGB').tobytes()
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
    return dict(matched_ceiling_fixture_pass=True, experiment=right["ceiling"] if drawing else "instant-blitter" if instant else "c2p", live_entry_checks=10 if drawing else 6,
                window='origin-load entry through cycle-complete entry',
                totals=totals, scenes=scenes,
                final_game_hunks_equal=final_hunks_equal, menu_pixels_equal=menu_equal,
                limitations=['The original limiter remains active.',
                             'Only the named drawing entries are bypassed; other rendering work remains.' if drawing else
                             'Instant blits alter hardware timing.' if instant else 'Bypassed conversion intentionally invalidates planar output.',
                             'A single matched pair does not establish variability or physical CPU performance.',
                             'This comparison does not complete the phase 4 matrix gate.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control', type=Path)
    parser.add_argument('candidate', type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.control, args.candidate), indent=2))
