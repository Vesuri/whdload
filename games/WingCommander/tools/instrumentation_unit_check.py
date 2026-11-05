#!/usr/bin/env python3
"""Shared recorder/schema/native-contract correctness; CPU models are not timers."""
import argparse
import ctypes as C
import json
from pathlib import Path
import struct
from c2p_check import CPU, BASE, STACK, STOP, u, ck, P, I, Q, Z, reference
from shared_cpu_check import assemble
from recorder_source import source, ROOT
from frame_schema import encode_frames, decode_frames, encode_display, decode_display, display_order
from native_validation import state, dma_regions, chunky_pixels, planar_pixels
from variants import get

DATA, BUFFER = 0x40000, 0xa0000


class Recorder:
    def __init__(self, blob, symbols, variant, model, capacity=8):
        self.c = CPU(blob, model); self.sy = symbols; self.v = get(variant)
        self.extent = 16+4*capacity
        self.clock = DATA+self.v.A4_BASE+self.v.A4['field_clock']
        ck(u.uc_mem_map(self.c.h, 0xdff000, 4096, 7))
        self.samples = [120]; self.reads = 0; self.instructions = 0
        self.advance = False
        def read(handle, kind, address, size, value, data):
            if address == 0xdff004:
                line = self.samples[min(self.reads, len(self.samples)-1)]
                self.c.write(address, struct.pack('>I', line << 8)); self.reads += 1
                if self.advance:
                    self.c.write(self.clock, struct.pack('>I', self.field()+1))
        def instruction(handle, address, size, data):
            self.instructions += 1
        self.callbacks = [C.CFUNCTYPE(None, P, I, Q, I, C.c_int64, P)(read),
                          C.CFUNCTYPE(None, P, Q, I, P)(instruction)]
        for kind, callback, begin, end in ((1 << 10, self.callbacks[0], 0xdff004, 0xdff007),
                                           (4, self.callbacks[1], 1, 0)):
            handle = Z(); ck(u.uc_hook_add(self.c.h, C.byref(handle), kind, callback, None, begin, end))
        self.c.write(BUFFER-32, b'\xa5'*(self.extent+64))

    def field(self, value=None):
        if value is not None: self.c.write(self.clock, struct.pack('>I', value))
        return int.from_bytes(self.c.read(self.clock, 4), 'big')

    def variable(self, name):
        return int.from_bytes(self.c.read(BASE+self.sy[name], 4), 'big')

    def call(self, entry, event=3, flags=0, supervisor=False, args=None):
        c = self.c
        c.reg(17, (0x2000 if supervisor else 0) | flags)
        for r in range(1, 17): c.reg(r, 0x23450000+r)
        c.reg(8, STACK)
        for r, val in (args or {}).items(): c.reg(r, val)
        c.write(STACK, struct.pack('>IH', STOP, event))
        before = [c.reg(r) for r in range(1, 18)]
        native = c.read(DATA, 0x10000)
        c.writes = []; self.reads = 0; self.instructions = 0
        ck(u.uc_emu_start(c.h, BASE+self.sy[entry], STOP, 1000000, 2000))
        assert c.reg(18) == STOP, 'unbounded recorder'
        after = [c.reg(r) for r in range(1, 18)]
        assert before[:7]+before[8:] == after[:7]+after[8:], 'register/CCR corruption'
        assert after[7] == STACK+4
        if not self.advance: assert c.read(DATA, 0x10000) == native, 'native data changed'
        for address, size in c.writes:
            assert any(lo <= address and address+size <= hi for lo, hi in (
                (STACK-128, STACK), (BUFFER, BUFFER+self.extent),
                (BASE+self.sy['frame_stats_buffer'], BASE+self.sy['timing_active']+2))), ('unexpected write', address)
        assert c.read(BUFFER-32, 32) == b'\xa5'*32 and c.read(BUFFER+self.extent, 32) == b'\xa5'*32
        return self.instructions

    def begin(self, flags=0, supervisor=False, **args):
        return self.call('recorder_begin', flags=flags, supervisor=supervisor,
                         args={1:args.get('buffer', BUFFER), 2:args.get('data', DATA), 9:args.get('hz', 50)})


def recorder_checks(out):
    results = []
    for variant, models in (('ocs', (1, 2, 4)), ('cd32', (2, 4))):
        v = get(variant)
        blob, sy = assemble(out, 'recorder-'+variant, source(variant, 8), v.CPU)
        for model in models:
            r = Recorder(blob, sy, variant, model); maximum = 0; cases = 0
            for supervisor in (False, True):
                for flags in range(32):
                    r.field(100); maximum = max(maximum, r.begin(flags, supervisor))
                    # First active call establishes the epoch, as in the CD32 recorder.
                    maximum = max(maximum, r.call('frame_stat', flags=flags, supervisor=supervisor))
                    r.field(101)
                    maximum = max(maximum, r.call('frame_stat', event=17, flags=flags, supervisor=supervisor))
                    maximum = max(maximum, r.call('recorder_end', flags=flags, supervisor=supervisor))
                    assert decode_frames(r.c.read(BUFFER, 20)) == (50, 0, [(17, 1, 120)])
                    before = r.c.read(BUFFER, 48)
                    r.call('frame_stat', flags=flags, supervisor=supervisor)
                    assert r.c.read(BUFFER, 48) == before, 'write after freeze'
                    cases += 1
            # Stable, torn line, field change, full, disabled and wrap boundaries.
            for hz in (50, 60):
                r.samples = [120]; r.field(0xffffffff); r.begin(hz=hz); r.call('frame_stat')
                r.field(0)
                r.samples = [0, 256, 256, 256]
                maximum = max(maximum, r.call('frame_stat', event=3)); assert r.reads == 4
                r.call('recorder_end')
                assert decode_frames(r.c.read(BUFFER, 20)) == (hz, 0, [(3, 1, 256)])
                r.samples = [120]; r.field(100); r.begin(hz=hz); r.call('frame_stat')
                for i in range(10): r.call('frame_stat', event=3)
                assert r.variable('frame_stats_count') == 8
                r.call('recorder_end'); assert len(decode_frames(r.c.read(BUFFER, 48))[2]) == 8
                cases += 2
            for attempts in range(1, 5):
                r.samples = [120]; r.field(100); r.begin(); r.call('frame_stat')
                r.samples = [0, 256]*(attempts-1)+[120, 120]
                maximum = max(maximum, r.call('frame_stat'))
                assert r.reads == 2*attempts and r.variable('frame_stats_count') == 1
            r.samples = [120]; r.field(100); r.begin(); r.call('frame_stat')
            r.samples = [0, 256]*4
            maximum = max(maximum, r.call('frame_stat'))
            assert r.reads == 8 and r.variable('frame_stats_count') == 0 and r.variable('frame_stats_dropped') == 1
            r.samples = [120]; r.advance = True
            maximum = max(maximum, r.call('frame_stat')); r.advance = False
            assert r.reads == 8 and r.variable('frame_stats_dropped') == 2
            r.call('frame_stat'); assert r.variable('frame_stats_count') == 1
            for args in ({'buffer':0}, {'data':0}, {'hz':49}):
                r.begin(**args); r.call('frame_stat'); r.call('recorder_end')
                assert r.variable('frame_stats_count') == 0
            r.c.close()
            results.append(dict(variant=variant, cpu_model=model, register_flag_cases=64, wrap_and_capacity_cases=cases-64,
                                max_executed_instructions=maximum, bounded_samples=4,
                                full_freeze_null_wrap_and_torn_checks=True))
    return results


def replay(out, exported, capture):
    """Run the ported recorder over observed events, with real native data bytes.

    Field/beam values are replay inputs, not live execution or a timing claim.
    Publication/IRQ events are serialised here; live IRQ use remains forbidden.
    """
    blob, sy = assemble(out, 'ocs-replay', source('ocs'), '68000')
    result = []
    for label in ('asteroids', 'fire'):
        expected = (exported/(label+'-framestats.bin')).read_bytes()
        hz, skip, events = decode_frames(expected)
        for model in (1, 2, 4):
            r = Recorder(blob, sy, 'ocs', model, 2048)
            native = (capture/(label+'-h1.bin')).read_bytes()
            r.c.write(DATA, native)
            epoch = int.from_bytes(native[0x77fe:0x7802], 'big')
            # Poison the CD32 location to prove it cannot supply the OCS epoch.
            r.c.write(DATA+0x7f02, struct.pack('>I', epoch+999))
            r.field(epoch); r.samples = [0]; r.begin(hz=hz); r.call('frame_stat')
            peak = 0
            for event, field, line in events:
                r.field((epoch+field)&0xffffffff); r.samples = [line]
                peak = max(peak, r.call('frame_stat', event=event))
            r.call('recorder_end')
            assert r.c.read(BUFFER, len(expected)) == expected, 'native event replay differs'
            assert r.variable('frame_stats_dropped') == 0
            r.c.close()
            result.append(dict(window=label, model=model, events=len(events),
                               peak_instructions=peak, exact_WCFS=True))
    return result


def recorder_sabotage(out):
    good = source('ocs', 8)
    rejected = []
    for name, old, new in (
            ('wrong_variant_clock', '$77fe(a0)', '$7f02(a0)'),
            ('missing_second_beam_read', 'move.l  $dff004,d3', 'move.l d0,d3')):
        assert old in good
        blob, sy = assemble(out, 'reject-'+name, good.replace(old, new), '68000')
        r = Recorder(blob, sy, 'ocs', 1)
        r.field(100); r.begin(); r.call('frame_stat')
        r.field(101); r.samples = [0, 256, 256, 256]
        r.call('frame_stat'); r.call('recorder_end')
        actual = decode_frames(r.c.read(BUFFER, 20))
        assert actual != (50, 0, [(3, 1, 256)]), 'oracle failed to distinguish corrupt recorder'
        r.c.close(); rejected.append(name)
    return rejected


def contracts():
    rejected = []
    def reject(label, action):
        try: action()
        except (ValueError, struct.error): rejected.append(label)
        else: raise AssertionError('accepted '+label)
    for vname in ('ocs', 'cd32'):
        v = get(vname)
        hunks = [bytes(h[2]) for h in v.HUNKS]; state(vname, hunks, hunks)
        bad = list(hunks); bad[1] = b'\x01'+bad[1][1:]
        reject(vname+' changed native state', lambda: state(vname, hunks, bad))
        bad[1] = bad[1][:-1]
        reject(vname+' truncated native state', lambda: state(vname, hunks, bad))
        width, height, row = 16, 4, 2
        plane = row*(height+v.BITMAP['leading_rows'])
        src = bytes((i*37+11)&255 for i in range(width*height))
        colours = chunky_pixels(vname, src, width, height)
        packed = bytearray(plane*v.BITMAP['depth'])
        for i, colour in enumerate(colours):
            for n in range(v.BITMAP['depth']):
                if colour & (1 << n): packed[n*plane+(i//width+v.BITMAP['leading_rows'])*row+(i%width)//8] |= 1 << (7-i%8)
        assert planar_pixels(vname, packed, width, height, row, plane) == colours
        if vname == 'cd32':
            assert bytes(packed) == reference(src), 'independent numpy CD32 packing differs'
        assert colours == (src if vname == 'cd32' else bytes(
            ((src[y*width+x]//16) if (x+y)%2 == 0 else src[y*width+x])%16
            for y in range(height) for x in range(width)))
        reject(vname+' truncated planes', lambda: planar_pixels(vname, packed[:-1], width, height, row, plane))
    reject('unknown variant', lambda: chunky_pixels('unknown', b'\0', 1, 1))
    headers = [(2, 0x100, 0x80000), (4, 0x200000, 0x600000)]
    dma_regions([(0x1000, 0x2000), (0x3000, 0x4000)], headers)
    for name, regions in (('Fast DMA', [(0x200000,0x201000)]), ('overlap', [(0x1000,0x2000),(0x1800,0x2800)]),
                           ('unaligned', [(0x1001,0x2000)]), ('outside Chip header', [(0x80,0x200)])):
        reject(name, lambda: dma_regions(regions, headers))
    raw = encode_frames(50, [(3, 0, 10), (17, 1, 20)])
    for name, bad in (('truncated header', raw[:15]), ('truncated record', raw[:-1]),
                      ('unknown event', raw[:16]+struct.pack('>I',31 << 27)+raw[20:])):
        reject(name, lambda: decode_frames(bad))
    rows = [(0, 40, 0, 0x1000, 0x5000), (1, 40, 1, 0x3000, 0x6000)]
    assert decode_display(encode_display(50, rows))[2] == rows
    display_order(rows)  # OCS is NOT constrained by the CD32 line 4..16 policy.
    reject('duplicate displayed buffer', lambda: display_order([rows[0], (1,40,0,0x1000,0x5000)]))
    reject('two displays in one field', lambda: display_order([rows[0], (0,50,1,0x3000,0x6000)]))
    return rejected


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', type=Path, required=True)
    p.add_argument('--replay', type=Path, help='OCS exported schema directory')
    p.add_argument('--capture', type=Path, help='matching native OCS on capture')
    a = p.parse_args()
    if bool(a.replay) != bool(a.capture): p.error('--replay and --capture must be paired')
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:
        p.error('new tmp output required')
    a.output.mkdir(parents=True)
    result = dict(recorders=recorder_checks(a.output), rejected=contracts(), recorder_mutations_rejected=recorder_sabotage(a.output), passed=True,
                  limit='CPU semantic/instruction-count checks, not execution-time measurements')
    if a.replay:
        result['replay'] = replay(a.output, a.replay, a.capture)
    (a.output/'report.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
