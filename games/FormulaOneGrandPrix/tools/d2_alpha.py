#!/usr/bin/env python3
"""D2 presentation phase α of every picture, recomputed and judged against its display.

  d2_alpha.py CAPTURE [--out tmp/...json]

CAPTURE is a c2_capture --states --alpha directory. Each record is the slave state
from c2_serial to d1_current, saved after d2_picture stored α. The check recomputes
the phase, the next interval, the lead and α with the slave's integer rule. The lead is
then judged against the one measured when the picture reached the screen (the next
record). The displayed world time, tick + α, must never go backwards. D10: the history's
weight d2_weight is recomputed too; a picture shows tick - weight, a tick plus the longer
measured lead before its display, which must not go backwards either, except after a
picture at α 0 that shows cur (the first of an epoch, at a cut), counted apart; the
pictures clamped to the history or to cur are counted.
"""
import argparse
import collections
import gzip
import hashlib
import json
from pathlib import Path
import struct

TICK, REPEAT = 0, 2
Q14 = 1 << 14


def regions(base, symbols):
    """One contiguous region: c2_serial .. c2_clock .. c2_beam_max, then the d2 block."""
    start, end = symbols['c2_serial'], symbols['d1_current']
    assert symbols['c2_clock'] < symbols['d2_start'] < symbols['d2_leads'] < end
    return [(base+start, end-start)]


def interval(quot, rem, phase):
    """world_clock_interval (F3): whole fields from this tick's deadline to the next's,
    ceil(k x step x F / 65536); the stock step gives PAL 7,6,6,6 and NTSC 8,7."""
    following = (phase + rem) & 0xffff
    return quot + (phase + rem > 0xffff) + (following != 0) - (phase != 0)


def alpha(phase, lead, period, fields):
    """The slave's rule: α 0 when pictures are longer than the two-tick horizon, else Q14
    clamped to two ticks (D9: a single picture just over a tick still predicts)."""
    if max(lead, period) > 2*fields:
        return 0, True
    total = phase + lead
    return (2*Q14 if total >= 2*fields else (total*Q14)//fields), False


def weight(alpha_value, phase, lead, leads, fields):
    """The slave's D10 rule: the history's weight, Q14, from the fields past a tick plus
    the longer lead; cur (0) at α 0 or a tick or more, the history (Q14) before it."""
    if alpha_value == 0:
        return 0
    total = phase + lead - max(leads)
    return Q14 if total < 0 else 0 if total >= fields else Q14 - (total*Q14)//fields


def decode(record, symbols):
    at = lambda name: symbols[name]-symbols['c2_serial']
    word = lambda name: struct.unpack_from('>H', record, at(name))[0]
    long = lambda name: struct.unpack_from('>I', record, at(name))[0]
    clock = dict(zip(('last','credit','rate','phase','batch','observed','consumed','dropped','ticks',
                      'quot','rem','limit','step'),
                     struct.unpack_from('>I4H4I4H', record, at('c2_clock'))))
    return dict(serial=long('c2_serial'), clock=clock, mode=word('c2_mode'),
                draw_mode=word('c2_draw_mode'), start=long('d2_start'),
                pictures=long('d2_pictures'), latest=long('d2_latest'), kind=word('d2_kind'),
                pending=word('d2_pending'), phase=word('d2_phase'), interval=word('d2_interval'),
                lead=word('d2_lead'), period=word('d2_period'), alpha=word('d2_alpha'),
                leads=struct.unpack_from('>2H', record, at('d2_leads')), weight=word('d2_weight'))


def percentile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered)-1, int(p*len(ordered)))] if ordered else None


def check(directory):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    assert meta['status'] == 'CAPTURED' and meta['quit'] == 'OK', directory
    info = meta['states']['pictures']
    archive = (root/'pictures.bin.gz').read_bytes()
    assert hashlib.sha256(archive).hexdigest() == info['archive_sha256']
    symbols = {k: int(v, 16) if isinstance(v, str) else v for k, v in meta['symbols'].items()}
    size = info['regions'][0][1]
    data = gzip.decompress(archive)
    assert len(data) == size*info['count']
    items = [decode(data[n*size:(n+1)*size], symbols) for n in range(info['count'])]
    failures, errors, display, latest = [], [], [], 0
    kinds = collections.Counter()
    alphas = collections.Counter()
    weights = collections.Counter()
    for n, item in enumerate(items):
        c = item['clock']
        kinds['tick' if item['kind'] == TICK else 'repeat'] += 1
        expected_phase = (item['start'] - c['last'] + c['credit']) & 0xffff
        fields = interval(c['quot'], c['rem'], c['phase'])
        period = item['period']
        previous = items[n-1] if n else None
        if previous and item['pictures'] == previous['pictures']+1:
            want = min(0x7fff, item['start']-previous['start'])
            if period != want:
                failures.append(dict(picture=n, period=period, expected=want))
        expected_alpha, longest = alpha(item['phase'], item['lead'], period, item['interval'])
        latest += longest
        problems = []
        if item['phase'] != expected_phase:
            problems.append(('phase', item['phase'], expected_phase))
        if item['interval'] != fields:
            problems.append(('interval', item['interval'], fields))
        if item['lead'] != item['leads'][item['kind']//2]:
            problems.append(('lead', item['lead'], item['leads']))
        if item['alpha'] != expected_alpha:
            problems.append(('alpha', item['alpha'], expected_alpha))
        expected_weight = weight(item['alpha'], item['phase'], item['lead'], item['leads'], item['interval'])
        if item['weight'] != expected_weight:
            problems.append(('weight', item['weight'], expected_weight))
        if item['alpha']:
            weights['history' if item['weight'] == Q14 else 'cur' if item['weight'] == 0 else 'between'] += 1
        if item['latest'] != (previous['latest'] if previous else item['latest']-longest) + longest:
            problems.append(('latest count', item['latest']))
        if problems:
            failures.append(dict(picture=n, problems=problems))
        alphas[min(8, item['alpha']*4//Q14)] += 1
        # World state drawn: inside a tick the new state (counted at the pacer), else the last.
        tick = c['ticks'] + (1 if item['kind'] == TICK else 0)
        nxt = items[n+1] if n+1 < len(items) else None
        if nxt is None:
            continue
        measured = nxt['leads'][item['kind']//2]
        shown = item['start'] + measured
        if not longest:
            errors.append(item['lead'] - measured)
        ideal = tick + (item['phase'] + measured)/item['interval']
        drawn = tick + item['alpha']/Q14
        display.append(dict(picture=n, shown=shown, tick=tick, drawn=drawn, ideal=ideal, mode=item['mode'],
                            error_fields=(drawn-ideal)*item['interval'], latest=longest,
                            time=tick - item['weight']/Q14, alpha=item['alpha']))
    # Ticks restart when a replay starts or ends (a new epoch, with a change of loop mode).
    backwards = [(a['picture'], a['drawn'], b['drawn']) for a, b in zip(display, display[1:])
                 if b['drawn'] < a['drawn'] - 1e-9 and a['mode'] == b['mode']]
    time_backwards = [(a['picture'], a['time'], b['time']) for a, b in zip(display, display[1:])
                      if b['time'] < a['time'] - 1e-9 and a['mode'] == b['mode']]
    after_latest = [t for t in time_backwards if not display[t[0]]['alpha']]
    time_backwards = [t for t in time_backwards if display[t[0]]['alpha']]
    predicted = [d['error_fields'] for d in display if not d['latest']]
    ideal = [d['ideal']-d['tick'] for d in display if not d['latest']]
    absolute = [abs(e) for e in predicted]
    lead_hist = collections.Counter(errors)
    result = dict(
        status='PASS' if not failures and not backwards and not time_backwards else 'FAIL',
        pictures=len(items), kinds=dict(kinds), latest=latest,
        latest_share=latest/len(items),
        alpha_quarters={f'{q/4:.2f}': alphas[q] for q in sorted(alphas)},
        lead_error_fields=dict(exact=lead_hist.get(0, 0), count=len(errors),
                               histogram={str(k): v for k, v in sorted(lead_hist.items())}),
        display_error_fields=dict(p50=percentile(absolute, .5), p95=percentile(absolute, .95),
                                  max=max(absolute) if absolute else None),
        ideal_alpha=dict(p50=percentile(ideal, .5), p95=percentile(ideal, .95),
                         max=max(ideal) if ideal else None,
                         over_one=sum(a > 1 for a in ideal), over_two=sum(a > 2 for a in ideal)),
        backwards=backwards[:20], backwards_count=len(backwards),
        weights=dict(weights), time_backwards=time_backwards[:20], time_backwards_count=len(time_backwards),
        time_backwards_after_latest=len(after_latest),
        failures=failures[:20], failure_count=len(failures),
        archive_sha256=info['archive_sha256'])
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--out')
    args = parser.parse_args()
    result = check(args.capture)
    text = json.dumps(result, indent=2)+'\n'
    if args.out:
        path = Path(args.out).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
            raise ValueError('output must stay in project tmp/')
        path.write_text(text)
    print(text)
