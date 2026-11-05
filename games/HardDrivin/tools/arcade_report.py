"""Arcade race timing (CUSTOM5=1) as the game ran it: arcade_report.py RUN...

RUN is a capture_clocks.py directory. Time left comes from every field's
record, the lap clock, race flags and gate from the 32-field flush samples.
Reports the start, the clock rates while racing, every award, the time out
and the race end, each crash (time left and lap clock from the crash to its
recovery) and each off-road deadline as armed.
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../tools/arcade'))
import amiga_feel as af   # noqa: E402

FIELD_H = 1421020 / 709379          # hundredths per PAL field


def h(v):
    d = lambda b: (b >> 4) * 10 + (b & 15)
    return d(v >> 16 & 255) * 6000 + d(v >> 8 & 255) * 100 + d(v & 255)


def mmss(x):
    return '%d:%05.2f' % (x // 6000, x % 6000 / 100)


def report(run):
    meta = json.load(open(os.path.join(run, 'metadata.json')))
    # MPH per G($9928): the native speedometer's 0.28, real MPH for arcade
    # handling (a world unit 0.1791 ft, not the speedometer's 0.3504)
    mph = 0.28 * 0.1791 / 0.3504 if meta.get('custom1') == 2 else 0.28
    R = af.records(run)
    counts = open(os.path.join(run, 'counts.bin'), 'rb').read()
    clocks = open(os.path.join(run, 'clocks.bin'), 'rb').read()
    n = [struct.unpack_from('>H', counts, i)[0] for i in range(0, len(counts), 2)]
    S, k = [], 0
    for i, c in enumerate(n):
        k += c
        b = clocks[i * 34:(i + 1) * 34]
        lap, qual, left = struct.unpack_from('>III', b, 0)
        S.append(dict(field=R[k - 1]['field'], lap=h(lap), qual=h(qual), left=h(left), out=b[12], race=b[16],
                      level=b[17], replay=b[19], deadline=struct.unpack_from('>I', b, 20)[0], started=b[27],
                      gate=b[33]))
    print('== %s: CUSTOM1=%d CUSTOM5=%d, %d fields' % (os.path.relpath(run), meta['custom1'], meta.get('custom5', 0),
                                                      len(R)))
    first = next((s for s in S if s['started']), None)
    pre = [r for r in R if first is None or r['field'] < first['field'] - 32]
    if pre:
        print('  before the start: time left %s..%s over %d fields' % (
            mmss(min(h(r['clock']) for r in pre)), mmss(max(h(r['clock']) for r in pre)), len(pre)))
    if first:
        print('  started by field %d: lap %s, time left %s, qualifying time %s, difficulty %d' % (
            first['field'], mmss(first['lap']), mmss(first['left']), mmss(first['qual']), first['level']))
    # rates over clean running flush intervals
    lap_h = left_h = fields = 0
    for a, b in zip(S, S[1:]):
        df = b['field'] - a['field']
        window = [r for r in R if a['field'] < r['field'] <= b['field']]
        clean = (a['started'] and b['started'] and a['gate'] and b['gate'] and not a['replay'] and not b['replay']
                 and not a['out'] and not b['out'] and b['lap'] >= a['lap'] and b['left'] <= a['left']
                 and not any(r['crash'] or r['recovery'] for r in window) and a['race'] and b['race'])
        if clean and df > 0 and a['left'] - b['left'] < 4 * df:
            lap_h += b['lap'] - a['lap']
            left_h += a['left'] - b['left']
            fields += df
    if fields:
        print('  racing: %d fields, lap clock %.5f and time left %.5f hundredths per field (real time %.5f)' % (
            fields, lap_h / fields, left_h / fields, FIELD_H))
    for a, b in zip(R, R[1:]):
        if h(b['clock']) > h(a['clock']):
            print('  award at field %d: %s -> %s (+%.2f s)' % (b['field'], mmss(h(a['clock'])), mmss(h(b['clock'])),
                                                              (h(b['clock']) - h(a['clock'])) / 100))
    zero = next((r for r in R if first and r['field'] > first['field'] and h(r['clock']) == 0), None)
    if zero:
        end = next((s for s in S if s['field'] >= zero['field'] and not s['race']), None)
        print('  time out at field %d, %.0f MPH; race over by field %s (%s s after)' % (
            zero['field'], zero['velocity'] * mph, end and end['field'],
            end and '%.2f' % ((end['field'] - zero['field']) * FIELD_H / 100)))
        later = [r for r in R if zero['field'] <= r['field'] <= (end['field'] if end else 1e9)]
        if later:
            print('    speed from %.0f to %.0f MPH meanwhile' % (later[0]['velocity'] * mph, later[-1]['velocity'] * mph))
    i = 0
    while i < len(R):
        if R[i]['crash'] and (i == 0 or not R[i - 1]['crash']):
            j = next((j for j in range(i, len(R)) if R[j]['recovery']), len(R) - 1)
            a = max((s for s in S if s['field'] < R[i]['field']), key=lambda s: s['field'], default=None)
            b = min((s for s in S if s['field'] > R[j]['field']), key=lambda s: s['field'], default=None)
            df = R[j]['field'] - R[i]['field']
            dl = h(R[i]['clock']) - h(R[j]['clock'])
            print('  crash at field %d, recovery at %d (%d fields): time left -%.2f s = %.4f per field '
                  '(5/16 of real time is %.4f)%s' % (
                      R[i]['field'], R[j]['field'], df, dl / 100, dl / max(df, 1), FIELD_H * 5 / 16,
                      '; lap clock %s..%s, flush fields %d..%d' % (mmss(a['lap']), mmss(b['lap']), a['field'], b['field'])
                      if a and b else ''))
            i = j + 1
        else:
            i += 1
    off = None
    for a, b in zip(R, R[1:]):
        if a['road'] and not b['road']:
            off = b['field']
        if b['road']:
            off = None
        if b['recovery'] and not a['recovery'] and not any(r['crash'] for r in R if b['field'] - 400 < r['field'] <= b['field']):
            print('  off-road recovery at field %d%s' % (b['field'], ', %.2f s after leaving the road' % (
                (b['field'] - off) * FIELD_H / 100) if off else ''))
    for a, b in zip(S, S[1:]):
        if b['deadline'] and b['deadline'] != a['deadline']:
            print('  off-road deadline at field %d: %s, lap %s, so %.2f s' % (
                b['field'], mmss(h(b['deadline'])), mmss(b['lap']), (h(b['deadline']) - b['lap']) / 100))


for run in sys.argv[1:]:
    report(run)
