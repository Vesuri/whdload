#!/usr/bin/env python3
"""Recompute the complete chunky census from raw sources; optionally check recording neutrality."""
import argparse
import collections
import json
from pathlib import Path
from PIL import Image
from matrix_report import report


def check(run, oracle=None):
    meta = json.loads((run/'result.json').read_text())
    if not meta['complete'] or not meta.get('raw_chunky'):
        raise ValueError('completed raw-source capture required')
    if meta.get('profiles', True) and meta['machine']=='a1200-fast':
        report(run)  # Retain the stronger established 020 profile checks.
    else:
        from matrix_scene_report import report as scene_report
        scene_report(run)
    scenes = collections.defaultdict(lambda: dict(calls=0, pairs=0, compared_bytes=0,
                                                 changed_bytes=0, changed_blocks=0, sizes=set()))
    oracle_sources = {}
    matched_sources = 0
    if oracle:
        from matrix_census_check import check as check_oracle
        check_oracle(oracle)
        oracle_meta = json.loads((oracle/'result.json').read_text())
        for key in ('machine', 'options', 'audit_cacr', 'slave_sha256'):
            if oracle_meta[key] != meta[key]:
                raise ValueError('unmatched GDB oracle configuration: '+key)
        oracle_sources = {(sample['scene'], sample['index']): (oracle/sample['file']).read_bytes()
                          for sample in oracle_meta['chunky_oracle']}
    prior_scene = None
    previous = None
    total = 0
    with (run/'chunky-sources.bin').open('rb') as source:
        for line in (run/'matrix-events.txt').read_text().splitlines():
            fields = line.split()
            if fields[0] != 'C':
                continue
            scene = int(fields[1])
            size, paired, changed, blocks = map(int, fields[4:8])
            data = source.read(size)
            if len(data) != size:
                raise ValueError('truncated raw source stream')
            if scene != prior_scene:
                previous = None
            compared = previous is not None and len(previous) == size
            expected_bytes = sum(a != b for a, b in zip(data, previous)) if compared else 0
            expected_blocks = sum(data[p:p+32] != previous[p:p+32] for p in range(0, size, 32)) if compared else 0
            if (paired, changed, blocks) != (int(compared), expected_bytes, expected_blocks):
                raise ValueError(f'raw census mismatch at call {total}, scene {scene}')
            entry = scenes[scene]
            key = (scene, entry['calls'])
            if key in oracle_sources:
                if data != oracle_sources[key]:
                    raise ValueError('raw source differs from independent GDB snapshot')
                matched_sources += 1
            entry['calls'] += 1
            entry['sizes'].add(size)
            if compared:
                entry['pairs'] += 1
                entry['compared_bytes'] += size
                entry['changed_bytes'] += expected_bytes
                entry['changed_blocks'] += expected_blocks
            previous, prior_scene = data, scene
            total += 1
        if source.read(1):
            raise ValueError('unconsumed raw source bytes')
    if not total:
        raise ValueError('empty census')
    if matched_sources != len(oracle_sources):
        raise ValueError('missing independent source sample')
    output = []
    for index, entry in sorted(scenes.items()):
        entry['sizes'] = sorted(entry['sizes'])
        entry['changed_fraction'] = entry['changed_bytes']/entry['compared_bytes'] if entry['compared_bytes'] else None
        output.append(dict(scene=meta['names'][index], **entry))
    return dict(raw_census_pass=True, calls=total, scenes=output, gdb_source_samples_matched=matched_sources, validated_timing_baseline=False,
                scope='Independent recomputation from every observed source buffer; the separate GDB oracle checks source acquisition in its sampled window.')


def compare(control, candidate):
    left = json.loads((control/'result.json').read_text())
    right = json.loads((candidate/'result.json').read_text())
    for key in ('machine', 'options', 'audit_cacr', 'emulator_sha256', 'slave_sha256', 'hunks', 'slave', 'boot_cpu', 'live_cpu'):
        if left[key] != right[key]:
            raise ValueError('unmatched configuration: '+key)
    if not left['complete'] or not right['complete'] or left.get('diagnostic_stops') or right.get('diagnostic_stops'):
        raise ValueError('neutrality comparison requires complete runs without oracle stops')
    a = (control/'matrix-events.txt').read_text().splitlines()
    b = (candidate/'matrix-events.txt').read_text().splitlines()
    if a != b:
        at = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        raise ValueError(f'observer ledger differs at record {at}; lengths {len(a)}/{len(b)}')
    profiles = left.get('profiles', True) and right.get('profiles', True)
    for index in range(34):
        name = f'scene-{index:02d}.aprof'
        if profiles:
            if (control/name).read_bytes() != (candidate/name).read_bytes():
                raise ValueError('scene profile differs: '+name)
        for directory, metadata in ((control,left),(candidate,right)):
            if not metadata.get('profiles',True) and (directory/name).exists():
                raise ValueError('unexpected aggregate profile in disabled run')
    raw_sources_identical = None
    if left.get('raw_chunky') and right.get('raw_chunky'):
        with (control/'chunky-sources.bin').open('rb') as raw_a, (candidate/'chunky-sources.bin').open('rb') as raw_b:
            while True:
                block_a, block_b = raw_a.read(1 << 20), raw_b.read(1 << 20)
                if block_a != block_b:
                    raise ValueError('recorded source buffers differ')
                if not block_a:
                    break
        raw_sources_identical = True
    memory_a = (control/'fast.bin').read_bytes()
    memory_b = (candidate/'fast.bin').read_bytes()
    for base, size in zip(left['hunks'], (0x35ea4, 0xfda0, 4, 0x1590)):
        offset = base-0x200000
        if memory_a[offset:offset+size] != memory_b[offset:offset+size]:
            raise ValueError('final allocated game hunk differs')
    with Image.open(control/'menu.png') as image_a, Image.open(candidate/'menu.png') as image_b:
        if image_a.size != image_b.size or image_a.convert('RGB').tobytes() != image_b.convert('RGB').tobytes():
            raise ValueError('menu pixels differ')
    changed = [key for key, default in (('raw_chunky',False),('profiles',True),('host_warp',False))
               if left.get(key,default) != right.get(key,default)]
    return dict(matched_execution_pass=True, changed_features=changed,
                recording_neutrality_pass=changed==['raw_chunky'],
                aggregate_profiler_neutrality_pass=changed==['profiles'],
                warp_neutrality_pass=changed==['host_warp'],
                ledger_records=len(a), profile_files_identical=profiles, raw_sources_identical=raw_sources_identical,
                final_game_hunks_identical=True, menu_pixels_identical=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--control', type=Path)
    parser.add_argument('--oracle', type=Path)
    parser.add_argument('--compare-only', action='store_true')
    args = parser.parse_args()
    if args.compare_only and not args.control:
        parser.error('--compare-only requires --control')
    result = {} if args.compare_only else check(args.run, args.oracle)
    if args.control:
        result['comparison'] = compare(args.control, args.run)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
