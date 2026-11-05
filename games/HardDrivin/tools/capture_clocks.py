"""Lap clock G($9790) and countdown G($9798) against PAL fields in a feel plan run.

capture_clocks.py OUT --plan NAME [--custom1 0|1|2] [--custom5 0|1] [--max-fields N] [--prefix P] [--traffic N]   (OUT below tmp/prof)

capture_feel.py's record loop, plus at every record flush the 16 bytes at
G($9790) (lap, qualifying time, time left, time out), the 16 at G($add4)
(race, difficulty, replay, off-road deadline, started) and the 2 at G($95ec)
(clock gate second) in clocks.bin (34 bytes a flush), the "OFF ROAD n" digits
G($8ce8..9) (digits.bin, 2 bytes a flush), with --traffic N the first N 46-byte traffic records (traffic.bin, at the
pointer G($af06)), and the record count (counts.bin), so each sample is the state at the last record of its flush.
Read-only. Use a distinct INSTANCE.
"""
import argparse
import json
import os
import shutil
import struct
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capture_demo import ROOT, command      # noqa: E402
from capture_session import Session         # noqa: E402

REC = 80
DONE, VCOUNT = 28, 34


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out')
    p.add_argument('--plan', required=True)
    p.add_argument('--custom1', type=int, choices=(0, 1, 2), default=2)
    p.add_argument('--custom5', type=int, choices=(0, 1), default=0)
    p.add_argument('--max-fields', type=int, default=12000)
    p.add_argument('--prefix', default='feel-')
    p.add_argument('--traffic', type=int, default=0)
    a = p.parse_args()
    os.chdir(ROOT)
    out = (ROOT / a.out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(ROOT / 'tmp/build' / ('%s%s.slave' % (a.prefix, a.plan)), out / 'slave.slave')
    s = Session(out, 'a500', out / 'slave.slave', 0x10ed4)
    s.env['WHD_ARGS'] += ' CUSTOM1=%d CUSTOM5=%d' % (a.custom1, a.custom5)
    t0 = time.monotonic()
    try:
        s.boot()
        hits = []
        for bank, b in s.dump_banks('anchor'):
            for tag in (b'HDFEEL02', b'HDFEEL03'):    # 03 adds a sixth offset
                i = b.find(tag)
                while i >= 0:
                    hits.append((bank + i, struct.unpack_from('>5i', b, i + 8)))
                    i = b.find(tag, i + 1)
        assert len(hits) == 1, hits
        sig, offsets = hits[0]
        state, vbuf, _, flush_rec, _ = (sig + o for o in offsets)
        g = lambda x: s.layout['a4'] + x - 0x10000
        rel = out.relative_to(ROOT)
        count = '(*(unsigned short*)%#x)' % (state + VCOUNT)
        command('\n'.join([
            'gdb break *%#x' % flush_rec,
            'set $n=0',
            'while $n < %d && *(short*)%#x == 0' % (a.max_fields, state + DONE),
            'continue',
            'append binary memory %s/rec.bin %#x %#x+%d*%s' % (rel, vbuf, vbuf, REC, count),
            'append binary memory %s/clocks.bin %#x %#x' % (rel, g(0x9790), g(0x9790) + 16),
            'append binary memory %s/clocks.bin %#x %#x' % (rel, g(0xadd4), g(0xadd4) + 16),
            'append binary memory %s/clocks.bin %#x %#x' % (rel, g(0x95ec), g(0x95ec) + 2),
            'append binary memory %s/digits.bin %#x %#x' % (rel, g(0x8ce8), g(0x8ce8) + 2),
        ] + ([
            'append binary memory %s/traffic.bin *(unsigned*)%#x *(unsigned*)%#x+%d'
            % (rel, g(0xaf06), g(0xaf06), 46 * a.traffic)] if a.traffic else []) + [
            'append binary memory %s/counts.bin %#x %#x' % (rel, state + VCOUNT, state + VCOUNT + 2),
            'set $n=$n+%s' % count,
            'end',
            'delete']), timeout=1800)
        meta = dict(s.metadata, plan=a.plan, custom1=a.custom1, custom5=a.custom5,
                    records=len((out / 'rec.bin').read_bytes()) // REC, wall_seconds=round(time.monotonic() - t0, 1))
        (out / 'metadata.json').write_text(json.dumps(meta, indent=2) + '\n')
        print(a.plan, 'custom1', a.custom1, 'records', meta['records'], 'wall', meta['wall_seconds'], flush=True)
    finally:
        s.close()


if __name__ == '__main__':
    main()
