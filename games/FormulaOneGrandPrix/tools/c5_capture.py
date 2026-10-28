"""C5(a) world-tick rate over a whole Quick Race, used by c2_capture --rate.

Real time is emulated time: one PAL non-interlaced field is 313 lines of 227 colour
clocks at 3,546,895 Hz (49.92 Hz). The schedule funds 8 ticks per 50 fields, so the
expected rate is 7.987 ticks per second, inside the 8.00 ± 1% gate.
"""
import gzip
import hashlib
import json
import re
from fractions import Fraction
import struct

STEP = 250
LIMIT = 400                       # samples (100,000 fields) before giving up
PAL_FIELD = Fraction(313*227, 3546895)
CLOCK_STEP_MS = Fraction(2111*1000, 16384)   # native race-clock increment per tick
WORDS = ('c2_mode','c2_in_tick','c3_suspended','c3_inactive','c2_beam_max','c2_native_rate')
LONGS = ('c2_serial','c3_epochs','c3_exits','c3_rebased','c3_excluded','c3_pauses')


def decode(slave, session, symbols):
    """Rate fields of one sample, from its saved slave state and h0+$3A714–3A7D3."""
    item = {n: struct.unpack_from('>H', slave, symbols[n])[0] for n in WORDS}
    item.update({n: struct.unpack_from('>I', slave, symbols[n])[0] for n in LONGS})
    values = struct.unpack_from('>I4H4I', slave, symbols['c2_clock'])
    item['clock'] = dict(zip(('last','credit','rate','phase','batch','observed','consumed',
                              'dropped','ticks'), values))
    whole, fraction = struct.unpack_from('>IH', session, 0x3a77c-0x3a714)
    item['race_clock'] = [whole, fraction]          # milliseconds, 16-bit fraction
    item['start_phase'] = session[0x3a750-0x3a714]
    return item


def evaluate(samples):
    """C5(a) from decoded samples; shared by capture and report."""
    live = [s for s in samples if s['c2_mode'] == 1 and s['c3_epochs'] == samples[0]['c3_epochs']]
    first, last = live[0], live[-1]
    serial = last['c2_serial'] - first['c2_serial']
    seconds = serial * PAL_FIELD
    ticks = last['clock']['ticks'] - first['clock']['ticks']
    # Windows between consecutive live samples; a window with dropped debt did not fit.
    fit_ticks, fit_fields, runs, run, unfit = 0, 0, [], 0, []
    for a, b in zip(live, live[1:]):
        if b['clock']['dropped'] == a['clock']['dropped']:
            fit_ticks += b['clock']['ticks'] - a['clock']['ticks']
            fit_fields += b['c2_serial'] - a['c2_serial']
            run += 1
        else:
            unfit.append(dict(serial=a['c2_serial'], fields=b['c2_serial']-a['c2_serial'],
                              dropped=b['clock']['dropped']-a['clock']['dropped']))
            if run:
                runs.append(run)
            run = 0
    if run:
        runs.append(run)
    # Each contiguous fitting run can end with at most one second of credit (8 ticks)
    # and one reserved tick unaccounted at either end.
    bound = Fraction(9*2*len(runs), fit_ticks) if fit_ticks else None
    rate = Fraction(fit_ticks) / (fit_fields*PAL_FIELD) if fit_fields else None
    clocked = [s for s in live if s['race_clock'] != first['race_clock']]
    ms = lambda s: Fraction(s['race_clock'][0]) + Fraction(s['race_clock'][1], 65536)
    clock = None
    if len(clocked) >= 2:
        a, b = clocked[0], clocked[-1]
        dt = (b['c2_serial'] - a['c2_serial']) * PAL_FIELD
        dticks = b['clock']['ticks'] - a['clock']['ticks']
        clock = dict(from_serial=a['c2_serial'], to_serial=b['c2_serial'],
                     ratio=float((ms(b)-ms(a))/1000/dt),
                     ms_per_tick=float((ms(b)-ms(a))/dticks),
                     native_ms_per_tick=float(CLOCK_STEP_MS))
    # PASS: the fitting time measures within ±1% including the boundary bound.
    # OVERLOADED: too little fitting time to measure; outside the gate's envelope.
    modal = (last['c3_rebased']-first['c3_rebased']) or (last['c3_excluded']-first['c3_excluded'])
    if modal or rate is None:
        status = 'FAIL' if modal else 'OVERLOADED'
    elif abs(rate/8-1) + bound <= Fraction(1, 100):
        status = 'PASS'
    elif bound > Fraction(1, 100):
        status = 'OVERLOADED'
    else:
        status = 'FAIL'
    return dict(
        status=status,
        field_seconds=float(PAL_FIELD), beam_max=sorted({s['c2_beam_max'] for s in live}),
        live_samples=len(live), fields=serial, seconds=float(seconds), ticks=ticks,
        whole_rate=float(ticks/seconds), dropped=last['clock']['dropped']-first['clock']['dropped'],
        fitting_fields=fit_fields, fitting_ticks=fit_ticks, fitting_runs=runs,
        fitting_share=float(Fraction(fit_fields, serial)) if serial else None,
        rate=float(rate) if rate is not None else None,
        rate_error=float(rate/8-1) if rate is not None else None,
        rate_bound=float(bound) if bound is not None else None,
        unfit=unfit, race_clock=clock)


def rate(args, command, out, base, bases, symbols, meta):
    assert args.custom4 == 1 and args.route == 'quickrace'
    result = dict(status='INCOMPLETE', step=STEP, samples=[])
    meta['rate'] = result
    def sample(name):
        slave_path, session_path = out/(name+'-slave.bin'), out/(name+'-session.bin')
        command('gdb', f'dump binary memory {slave_path} {base:#x} {base+symbols["c2_beam_max"]+2:#x}')
        command('gdb', f'dump binary memory {session_path} {bases[0]+0x3a714:#x} {bases[0]+0x3a7d4:#x}')
        slave, session = slave_path.read_bytes(), session_path.read_bytes()
        item = dict(name=name, files=dict(slave=hashlib.sha256(slave).hexdigest(),
                                          session=hashlib.sha256(session).hexdigest()))
        item.update(decode(slave, session, symbols))
        c = item['clock']
        assert c['observed'] == (c['consumed']+c['credit']+c['dropped']+item['c3_rebased'])&0xffffffff, item
        result['samples'].append(item)
        (out/'rate.json').write_text(json.dumps(result, indent=2)+'\n')
        return item
    item = sample('s000')
    assert item['c2_mode'] == 1 and item['c2_native_rate'] in (50, 60), item
    for n in range(1, LIMIT):
        command('gdb', f'monitor fields {STEP}')
        item = sample(f's{n:03d}')
        if item['c2_mode'] == 0 and item['c3_exits']:
            break
    else:
        raise AssertionError('race did not reach its results')
    command('shot', str(out/'results.png'))
    result.update(evaluate(result['samples']))
    (out/'rate.json').write_text(json.dumps(result, indent=2)+'\n')


# C5(b): the state the native replay checkpoint copies (h0+$396AC), at each completed tick.
CARS = (1, 0x368, 0x1956-0x368)        # car records and session, h1+$368–1955
SESSION = (0, 0x3a714, 0x3a7bc-0x3a714)


def tick_header(blob, symbols):
    """Slave words from c2_serial to c2_beam_max at a tick's pacer entry."""
    at = lambda name: symbols[name]-symbols['c2_serial']
    values = struct.unpack_from('>I4H4I', blob, at('c2_clock'))
    return dict(serial=struct.unpack_from('>I', blob, 0)[0],
                pictures=struct.unpack_from('>I', blob, at('c2_pictures'))[0],
                batch=values[4], dropped=values[7],
                tick=values[8]+1,              # counted inside the pacer, after this stop
                draw_mode=struct.unpack_from('>H', blob, at('c2_draw_mode'))[0])


def states(args, command, out, base, bases, symbols, meta):
    """Stop at every completed live tick until the race closes its epoch."""
    assert args.route == 'quickrace'
    result = dict(status='INCOMPLETE', ranges=dict(cars=CARS, session=SESSION), ticks=[])
    meta['states'] = result
    header = (symbols['c2_serial'], symbols['c2_beam_max']+2)
    regions = [(base+header[0], header[1]-header[0]),
               (bases[CARS[0]]+CARS[1], CARS[2]),
               (bases[SESSION[0]]+SESSION[1], SESSION[2])]
    # A1 timing inputs at the route stop: the UI stream (drawn in VBL-bounded menu loops,
    # it seeds the simulation through the protection byte) and the gameplay stream.
    inputs = {}
    for key, (h, offset) in (('ui_rng', (2, 0x2a794)), ('gameplay_rng', (0, 0x3a7b0))):
        path = out/(key+'.bin')
        command('gdb', f'dump binary memory {path} {bases[h]+offset:#x} {bases[h]+offset+5:#x}')
        inputs[key] = path.read_bytes().hex()
    result['inputs'] = inputs
    paths = [out/f'ticks-{n}.bin' for n in range(3)]
    for path in paths:
        path.write_bytes(b'')
    # gdb appends each region at every tick's pacer entry and continues by itself,
    # so the whole race needs one client round trip; the epoch close stops it.
    appends = '\n'.join(f'append binary memory {path} {start:#x} {start+size:#x}'
                         for path, (start, size) in zip(paths, regions))
    command('gdb', 'delete breakpoints')
    command('gdb', f'break *{base+symbols["c2_pacer"]:#x}')
    command('gdb', f'condition $bpnum *(unsigned short*){base+symbols["c2_in_tick"]:#x} != 0')
    command('gdb', f'commands $bpnum\nsilent\n{appends}\ncontinue\nend')
    command('gdb', f'break *{base+symbols["c3_leave"]:#x}')
    command('gdb', 'continue')
    pc = int(re.search(r'\$\d+\s*=\s*(0x[0-9a-fA-F]+)', command('gdb', 'p/x $pc'))[1], 16)
    assert pc == base+symbols['c3_leave'], hex(pc)
    command('gdb', 'delete breakpoints')
    columns = [path.read_bytes() for path in paths]
    count = len(columns[0]) // regions[0][1]
    assert count and all(len(c) == count*size for c, (_, size) in zip(columns, regions)), count
    blobs = []
    for n in range(count):
        parts = [c[n*size:(n+1)*size] for c, (_, size) in zip(columns, regions)]
        item = tick_header(parts[0], symbols)
        item['sha256'] = hashlib.sha256(parts[1]+parts[2]).hexdigest()
        result['ticks'].append(item)
        blobs.append(b''.join(parts))
    for path in paths:
        path.unlink()
    (out/'ticks.bin.gz').write_bytes(gzip.compress(b''.join(blobs), mtime=0))
    result.update(status='PASS', record=len(blobs[0]), count=len(blobs),
                  archive_sha256=hashlib.sha256((out/'ticks.bin.gz').read_bytes()).hexdigest())
    (out/'states.json').write_text(json.dumps(result)+'\n')
