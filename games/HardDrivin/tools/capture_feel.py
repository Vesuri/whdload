"""Capture one plan step F manoeuvre (tools/feel_fixture.s).

capture_feel.py OUT --plan NAME [--profile P] [--custom1 0|1|2] [--custom5 0|1] [--custom4 0|1] [--custom2 N] [--slow N] [--max-fields N] [--timeout S]

OUT is a new directory below tmp/prof (relative to the game directory). Boots
tmp/build/feel-NAME.slave to native race entry. The fixture logs into two
buffers; at its flush routines the capture appends them to OUT/rec.bin (an
80-byte record per VBL) and OUT/steps.bin (a 92-byte pose per physics pass:
race field, fields the enhanced physics consumed, G($98fc)..G($994f)) and,
from HDFEEL03 slaves, OUT/model.bin (the first 80 bytes of the handling
model's state after each pass, zero unless CUSTOM1=2), until
the fixture reports its end or N fields have passed. Read-only: gdb writes
nothing to the guest. S (default 900) limits the wall time of the capture.
--slow N uses tmp/build/feel-slow-NAME.slave with CUSTOM4=N (N more fields per frame).
Use a distinct INSTANCE for each concurrent run.
"""
import argparse
import json
import os
import shutil
import struct
import time
from capture_demo import ROOT, command
from capture_session import Session
from machine_profiles import PROFILES

REC, POSE, MODEL = 80, 92, 80
DONE, VCOUNT, PCOUNT = 28, 34, 36


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--plan', required=True)
    p.add_argument('--profile', choices=PROFILES, default='a500')
    p.add_argument('--custom1', type=int, choices=(0, 1, 2), default=1)
    p.add_argument('--custom5', type=int, choices=(0, 1), default=0)
    p.add_argument('--custom4', type=int, choices=(0, 1), default=0, help='arcade brake: 0 full, 1 soft (not with --slow)')
    p.add_argument('--custom2', type=int, default=0, help='frame delay')
    p.add_argument('--prefix', default='feel-', help='slave name prefix (build_feel.py --prefix)')
    p.add_argument('--slow', type=int, default=0)
    p.add_argument('--max-fields', type=int, default=12000)
    p.add_argument('--timeout', type=int, default=900)
    p.add_argument('--crash-sites', action='store_true',
                   help='log which native crash writer fires (bce0 objects, bdbe traffic, bfee walls, cc54 landing) to crash.txt')
    p.add_argument('--break-tag', help='ASCII tag in the slave; break 8 bytes after it each time and log the road state (debug builds)')
    a = p.parse_args()
    os.chdir(ROOT)
    out = (ROOT / a.out).resolve()
    assert not any(c.isspace() for c in str(out.relative_to(ROOT / 'tmp/prof')))
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(ROOT / 'tmp/build' / ('%s%s%s.slave' % (a.prefix, 'slow-' if a.slow else '', a.plan)),
                    out / 'slave.slave')
    assert not (a.slow and a.custom4), 'CUSTOM4 is the slow build\'s delay'
    s = Session(out, a.profile, out / 'slave.slave', 0x10ed4, a.slow or a.custom4)
    s.env['WHD_ARGS'] += ' CUSTOM1=%d CUSTOM5=%d CUSTOM2=%d' % (a.custom1, a.custom5, a.custom2)
    t0 = time.monotonic()
    try:
        s.boot()
        # HDFEEL03 adds the handling model's state after each pass (model.bin)
        hits = []
        for bank, b in s.dump_banks('anchor'):
            for tag, n in ((b'HDFEEL02', 5), (b'HDFEEL03', 6)):
                i = b.find(tag)
                while i >= 0:
                    hits.append((bank + i, struct.unpack_from('>%di' % n, b, i + 8)))
                    i = b.find(tag, i + 1)
        assert len(hits) == 1, hits
        sig, offsets = hits[0]
        state, vbuf, pbuf, flush_rec, flush_steps = (sig + o for o in offsets[:5])
        mbuf = sig + offsets[5] if len(offsets) > 5 else None
        rel = out.relative_to(ROOT)

        def count(off):
            return '(*(unsigned short*)%#x)' % (state + off)
        steps_dump = 'append binary memory %s/steps.bin %#x %#x+%d*%s' % (rel, pbuf, pbuf, POSE, count(PCOUNT))
        if mbuf is not None:
            steps_dump += '\nappend binary memory %s/model.bin %#x %#x+%d*%s' % (rel, mbuf, mbuf, MODEL, count(PCOUNT))
        base = s.layout['code_base']
        sites = [base + o for o in (0xbce0, 0xbdbe, 0xbfee, 0xcc54)] if a.crash_sites else []
        site_lines = []
        for k, addr in enumerate(sites):
            site_lines += ['%sif $pc == %#x' % ('' if k == 0 else 'else\n', addr),
                           'printf "CRASHSITE %%x after record %%d\\n", $pc - %#x, $n' % (base,)]
            if a.crash_sites and k in (0, 1):
                g = lambda off: s.layout['a4'] + off - 0x10000
                site_lines += ['printf "CRASHOBJ at %%d %%d mph %%d\\n", *(unsigned short*)%#x, *(unsigned short*)%#x, *(short*)%#x'
                               % (g(0x98f6), g(0x98fa), g(0x992c)), 'x/16hx $a3']
            if a.crash_sites and k == 2:
                g = lambda off: s.layout['a4'] + off - 0x10000
                site_lines += ['printf "CRASHWALL from %%d %%d to %%d %%d count %%d\\n", *(unsigned short*)%#x, *(unsigned short*)%#x, *(unsigned short*)%#x, *(unsigned short*)%#x, *(short*)%#x'
                               % (g(0x98f0), g(0x98f4), g(0x98f6), g(0x98fa), g(0x9960)),
                               'printf "CRASHWALL segment\\n"', 'x/4hu $a2']
        if a.break_tag:
            tags = [bank + i for bank, b in s.dump_banks('tag') for i in [b.find(a.break_tag.encode())] if i >= 0]
            assert len(tags) == 1, tags
            g = lambda off: s.layout['a4'] + off - 0x10000
            sites.append(tags[0] + 8)
            site_lines += ['%sif $pc == %#x' % ('' if len(sites) == 1 else 'else\n', sites[-1]),
                           'printf "ROADF d0 %%d d1 %%d a0 %%#x n %%d xyz %%d %%d %%d stunt %%d cursor %%#x table %%#x %%#x\\n", $d0, $d1, $a0, $n, *(short*)%#x, *(short*)%#x, *(short*)%#x, *(unsigned char*)%#x, *(unsigned int*)%#x, *(unsigned int*)%#x, *(unsigned int*)%#x'
                           % (g(0x98f6), g(0x98f8), g(0x98fa), g(0x9950), g(0x98e4), g(0x98e0), g(0x9952))]
        site_lines += ['end'] * len(sites)
        reply = command('\n'.join([
            'gdb break *%#x' % flush_rec,
            'break *%#x' % flush_steps] + ['break *%#x' % x for x in sites] + [
            'set $n=0',
            'while $n < %d && *(short*)%#x == 0' % (a.max_fields, state + DONE),
            'continue',
            'if $pc == %#x' % flush_rec,
            'append binary memory %s/rec.bin %#x %#x+%d*%s' % (rel, vbuf, vbuf, REC, count(VCOUNT)),
            'set $n=$n+%s' % count(VCOUNT),
            'else'] + (site_lines[:-len(sites)] + ['else'] if sites else []) + [
            steps_dump] + (['end'] * len(sites) if sites else []) + [
            'end',
            'end',
            'if %s > 0' % count(PCOUNT),
            steps_dump,
            'end',
            'delete']), timeout=a.timeout)
        (out / 'gdb.txt').write_text(reply)
        if sites:
            (out / 'crash.txt').write_text(''.join(l + '\n' for l in reply.splitlines() if 'CRASH' in l or 'ROADF' in l or ':\t' in l))
        rec = (out / 'rec.bin').read_bytes()
        assert rec and len(rec) % REC == 0
        steps = (out / 'steps.bin').read_bytes() if (out / 'steps.bin').exists() else b''
        assert len(steps) % POSE == 0
        last = rec[-REC:]
        meta = dict(s.metadata, plan=a.plan, custom1=a.custom1, custom5=a.custom5, custom2=a.custom2, custom4=a.slow or a.custom4, signature=hex(sig),
                    records=len(rec) // REC,
                    steps=len(steps) // POSE, done=struct.unpack_from('>h', last, 60)[0],
                    last_field=struct.unpack_from('>I', last, 0)[0], wall_seconds=round(time.monotonic() - t0, 1))
        (out / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
        print(a.plan, 'records', meta['records'], 'steps', meta['steps'], 'done', meta['done'],
              'wall', meta['wall_seconds'], flush=True)
    finally:
        s.close()


if __name__ == '__main__':
    main()
