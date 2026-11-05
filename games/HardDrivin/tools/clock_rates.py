"""Lap clock and countdown rates per PAL field: clock_rates.py RUN...  (capture_clocks.py runs)

Older runs hold 16 bytes a flush, newer ones 34; the clocks come first in both.

Uses only flush intervals in which the countdown fell by exactly one hundredth
per field (both clocks gated on, no time bonus) and the lap clock did not reset.
"""
import json
import os
import struct
import sys


def bcd(v):
    d = lambda b: (b >> 4) * 10 + (b & 15)
    return d((v >> 16) & 255) * 6000 + d((v >> 8) & 255) * 100 + d(v & 255)


for run in sys.argv[1:]:
    meta = json.load(open(os.path.join(run, 'metadata.json')))
    rec = open(os.path.join(run, 'rec.bin'), 'rb').read()
    counts = open(os.path.join(run, 'counts.bin'), 'rb').read()
    clocks = open(os.path.join(run, 'clocks.bin'), 'rb').read()
    n = [struct.unpack_from('>H', counts, i)[0] for i in range(0, len(counts), 2)]
    stride = len(clocks) // len(n)
    assert sum(n) * 80 == len(rec) and len(n) * stride == len(clocks) and stride in (16, 34)
    samples, k = [], 0
    for i, c in enumerate(n):
        k += c
        field, down = struct.unpack_from('>I', rec, (k - 1) * 80)[0], struct.unpack_from('>I', rec, (k - 1) * 80 + 56)[0]
        lap, remaining = struct.unpack_from('>I', clocks, i * stride)[0], struct.unpack_from('>I', clocks, i * stride + 8)[0]
        assert remaining == down, (i, hex(remaining), hex(down))
        samples.append((field, bcd(lap), bcd(remaining)))
    fields = lap = 0
    for (f0, l0, r0), (f1, l1, r1) in zip(samples, samples[1:]):
        if f1 > f0 and r0 - r1 == f1 - f0 and l1 >= l0:
            fields += f1 - f0
            lap += l1 - l0
    if not fields:
        print('%-34s no intervals at the native countdown rate (CUSTOM5=1: use arcade_report.py)' % os.path.relpath(run))
        continue
    rate = lap / fields
    print('%-34s custom1 %d  %5d fields  lap clock %.4f hundredths/field = %.3f s per real s, '
          'X set at %.1f%% of VBLs; countdown 1.0000 = 0.500' % (
              os.path.relpath(run), meta['custom1'], fields, rate, rate * 0.5, (rate - 4 / 3) * 100))
