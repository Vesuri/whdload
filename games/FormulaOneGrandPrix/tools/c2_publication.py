#!/usr/bin/env python3
"""Audit C2's captured field window, not an entire race or modal transition.

Checks CPU/blitter bitmap writes against actual bitplane DMA, VBL/publication
counts, and replay-R cadence between complete publication boundaries.
Usage: c2_publication.py tmp/CAPTURE tmp/REPORT.json
"""
import collections
import gzip
import json
from pathlib import Path
import struct
import sys

from machine_matrix import sha
from race_profile import barto
from state_diff import SIZES, scratch


def audit(directory):
    path = scratch(directory)
    meta = json.loads((path/'meta.json').read_text())
    if (meta['status'] != 'CAPTURED' or meta['quit'] != 'OK'
            or meta['trace_sha256'] != sha(path/'trace.bin')
            or meta['tick_sha256'] != sha(path/'tick.bin.gz')
            or meta['build']['slave_sha256'] != sha(path/'slave.bin')):
        raise ValueError('incomplete or changed capture')
    snapshot = gzip.decompress((path/'tick.bin.gz').read_bytes())
    if len(snapshot) != sum(SIZES):
        raise ValueError('incomplete hunk snapshot')
    u32 = lambda offset: struct.unpack_from('>I', snapshot, offset)[0]
    first = u32(0x124a)
    stride = u32(sum(SIZES[:2])+0x231da)
    if stride != 32000:
        raise ValueError('unrecognised bitmap layout')
    buffers = (first, first+stride)
    trace = barto.load(str(path/'trace.bin'))
    expected_fields = meta.get('profile_fields', 50)
    if (expected_fields not in (50,100) or trace.pc_base
            or len(trace.fields) != expected_fields):
        raise ValueError('requires the recorded field count and absolute instruction PCs')
    symbols = meta['symbols']
    vbl_pc = meta['slave_base']+symbols['c2_vbl']
    publish_pc = meta['slave_base']+symbols['c2_submit_call']
    replay_pc = meta['hunk_bases'][2]+0x1dfb4
    totals = collections.Counter()
    failures = []
    fields = []
    publication_seen, overlays = False, 0
    for index, field in enumerate(trace.fields):
        reads, writes = set(), []
        for offset in range(0, len(field.dma), field.dma_size):
            data = field.dma
            kind = data[offset+29]
            register = struct.unpack_from('<H', data, offset)[0]
            address = struct.unpack_from('<I', data, offset+12)[0]
            bitmap = next((i for i, start in enumerate(buffers)
                           if start <= address < start+32000), None)
            if bitmap is None:
                continue
            if kind == 6:
                reads.add(bitmap)
            # Packed DMA records: CPU 0x11xx writes; blitter reg 0 is D.
            if (kind == 2 and data[offset+1] & 1) or (kind == 5 and register == 0):
                writes.append((kind, bitmap))
        if len(reads) != 1:
            failures.append(dict(field=index, reason='ambiguous scanout', buffers=sorted(reads)))
        displayed_writes = collections.Counter()
        for kind, bitmap in writes:
            name = 'cpu_writes' if kind == 2 else 'blitter_writes'
            totals[name] += 1
            if bitmap in reads:
                displayed_writes[name] += 1
        if displayed_writes:
            failures.append(dict(field=index, reason='write to scanned bitmap',
                                 counts=dict(displayed_writes)))
        counts = collections.Counter()
        offset = field.insn_off
        while offset < field.insn_end:
            pc = None
            while True:
                value = struct.unpack_from('<I', trace.data, offset)[0]
                offset += 4
                if value >= 0xffff0000:
                    break
                if pc is None:
                    pc = value
            offset += 68                 # D0–D7, A0–A7, SR
            if pc == vbl_pc:
                counts['vbl'] += 1
            elif pc == replay_pc:
                counts['replay_paint'] += 1
                overlays += 1
            elif pc == publish_pc:
                counts['publish'] += 1
                if publication_seen:
                    expected = 1 if meta['replay'] else 0
                    if overlays != expected:
                        failures.append(dict(field=index, reason='replay paint cadence',
                                             actual=overlays, expected=expected))
                    totals['complete_publication_intervals'] += 1
                publication_seen, overlays = True, 0
        if counts['vbl'] != 1 or counts['publish'] > 1:
            failures.append(dict(field=index, reason='callback/publication count', counts=dict(counts)))
        totals.update(counts)
        fields.append(dict(field=index, scanned_buffers=sorted(reads), **counts))
    if any(totals[name] == 0 for name in ('cpu_writes','blitter_writes','publish',
                                         'complete_publication_intervals')):
        failures.append(dict(reason='window did not exercise required write/publication paths'))
    return dict(status='FAIL' if failures else 'PASS', trace_sha256=meta['trace_sha256'],
                slave_sha256=meta['build']['slave_sha256'], totals=dict(totals),
                failures=failures, fields=fields,
                scope=f'Only this {expected_fields}-field window; excludes partial publication intervals at trace edges.')


if __name__ == '__main__':
    result = audit(sys.argv[1])
    scratch(sys.argv[2]).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'fields'}, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)
