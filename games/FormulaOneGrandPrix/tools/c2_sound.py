#!/usr/bin/env python3
"""Check C2 field-duration handoff and native pitch arithmetic in a captured window.

This is a clock/formula check, not an audio-quality or whole-race acceptance gate.
"""
import collections
import json
import struct
import sys

from machine_matrix import sha
from race_profile import barto
from state_diff import scratch


def audit(directory):
    path = scratch(directory)
    meta = json.loads((path/'meta.json').read_text())
    if (meta['status'] != 'CAPTURED' or meta['quit'] != 'OK'
            or meta['trace_sha256'] != sha(path/'trace.bin')
            or meta['build']['slave_sha256'] != sha(path/'slave.bin')):
        raise ValueError('incomplete or changed capture')
    slave = (path/'slave.bin').read_bytes()
    # Single-code-hunk slave: bind the timing store to verified build bytes.
    if len(slave) != struct.unpack_from('>I', slave, 28)[0]*4+36:
        raise ValueError('unrecognised slave container')
    pattern = bytes.fromhex('35410002426a0004')  # fields store, native work reset
    if slave.count(pattern) != 1:
        raise ValueError('ambiguous sound-duration store')
    duration_pc = meta['slave_base']+slave.index(pattern)-32
    vbl_pc = meta['slave_base']+meta['symbols']['c2_vbl']
    h0 = meta['hunk_bases'][0]
    trace = barto.load(str(path/'trace.bin'))
    if trace.pc_base or not trace.fields:
        raise ValueError('absolute CPU instruction records required')
    failures, rows = [], []
    counts = collections.Counter()
    previous_serial = duration = pitch = minimum = elapsed = None
    for index, field in enumerate(trace.fields):
        offset, vbls = field.insn_off, 0
        while offset < field.insn_end:
            pc = None
            while True:
                value = struct.unpack_from('<I', trace.data, offset)[0]
                offset += 4
                if value >= 0xffff0000:
                    break
                if pc is None:
                    pc = value
            regs = struct.unpack_from('<17I', trace.data, offset)
            offset += 68
            if pc == vbl_pc:
                vbls += 1
            elif pc == duration_pc:
                serial, duration = regs[:2]
                if previous_serial is not None:
                    expected = min((serial-previous_serial) & 0xffffffff, 32767)
                    if duration != expected:
                        failures.append(dict(field=index, reason='elapsed-field handoff',
                                             actual=duration, expected=expected))
                    counts['duration_pairs'] += 1
                previous_serial = serial
                counts['ticks'] += 1
            elif pc == h0+0x36288:
                pitch = regs[0] & 0xffff
                pitch = pitch-65536 if pitch & 0x8000 else pitch
            elif pc == h0+0x36294:
                elapsed, minimum = regs[2] & 0xffff, regs[3] & 0xffff
                if duration is not None and elapsed != duration:
                    failures.append(dict(field=index, reason='native sound duration changed'))
            elif pc == h0+0x362aa and pitch is not None and minimum is not None:
                if minimum not in ((7,8) if meta['clock']['rate'] == 60 else (6,7)):
                    raise ValueError('invalid native minimum')
                denominator = max(minimum, elapsed)
                ratio = (minimum << 14)//denominator
                expected = ((pitch*ratio*4) >> 16) & 0xffff
                actual = regs[0] & 0xffff
                if (actual != expected or regs[2] & 0xffff != denominator
                        or regs[3] & 0xffff != ratio):
                    failures.append(dict(field=index, reason='native pitch arithmetic'))
                rows.append(dict(field=index, elapsed=elapsed, minimum=minimum,
                                 input=pitch, output=actual))
                counts['nonzero_pitch'] += bool(pitch)
                counts['overrun'] += elapsed > minimum
                counts['short_spacing'] += elapsed < minimum
                pitch = minimum = elapsed = None
        if vbls != 1:
            failures.append(dict(field=index, reason='VBL cadence', actual=vbls))
    exercised = all(counts[k] for k in ('duration_pairs','nonzero_pitch','overrun','short_spacing'))
    return dict(status='FAIL' if failures else 'PASS' if exercised else 'INCOMPLETE',
                trace_sha256=meta['trace_sha256'], counts=dict(counts), failures=failures,
                samples=rows, scope='Captured field handoff and pitch formula; not audio quality.')


if __name__ == '__main__':
    result = audit(sys.argv[1])
    scratch(sys.argv[2]).write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'samples'}, indent=2))
    sys.exit(0 if result['status'] == 'PASS' else 1)
