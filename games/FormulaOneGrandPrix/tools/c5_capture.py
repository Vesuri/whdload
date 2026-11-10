"""C5(a) world-tick rate over a whole Quick Race, used by c2_capture --rate.

Real time is emulated time: one PAL non-interlaced field is 313 lines of 227 colour
clocks at 3,546,895 Hz (49.92 Hz). The schedule funds 8 ticks per 50 fields, so the
expected rate is 7.987 ticks per second, inside the 8.00 ± 1% gate. F3: the gate is
65536/step ± 1%, the step being the clock's (stock $2000; F1GP-Ed's or the 20 Hz step).
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
# D7: view keys pressed at a tick's pacer and released two ticks later, so the same
# presses reach the same native scans in every run. Ticks count from 1 in every epoch,
# so each press names its epoch: the race is epoch 1 until the replay (epoch 2), and
# epoch 3 after it. TV and rear chase of the player, then the replay; after it front
# chase, front chase of the next car, rear chase of it, onboard it (cockpit), TV of
# it, then the player in rear chase and back in the cockpit.
VIEWS = ((1, 400, 0x4f), (1, 800, 0x5f), (3, 100, 0x46), (3, 400, 0x4d), (3, 600, 0x5f),
         (3, 900, 0x4e), (3, 1200, 0x4f), (3, 1500, 0x3d), (3, 1600, 0x5f), (3, 1800, 0x4e))
# And a replay in rear chase: Space at this tick's pacer pauses; R pressed in the
# pause starts the replay and is released when it starts; Space pressed in the pause
# the replay returns to resumes the race and is released at the resume. The pause
# wait ignores a key already down when it begins, so each press in a pause waits
# PAUSE_FIELDS. The gdb convenience variable $replay counts the steps. Steps are rare
# events; the field hook c2_vbl is a breakpoint only while a press is waiting, because
# a stop at every field would stall the emulator.
REPLAY = 1100
PAUSE_FIELDS = 25


def decode(slave, session, symbols):
    """Rate fields of one sample, from its saved slave state and h0+$3A714–3A7D3."""
    item = {n: struct.unpack_from('>H', slave, symbols[n])[0] for n in WORDS}
    item.update({n: struct.unpack_from('>I', slave, symbols[n])[0] for n in LONGS})
    values = struct.unpack_from('>I4H4I4H', slave, symbols['c2_clock'])
    item['clock'] = dict(zip(('last','credit','rate','phase','batch','observed','consumed',
                              'dropped','ticks','quot','rem','limit','step'), values))
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
    # Each contiguous fitting run can end with at most one second of credit (65536/step
    # ticks) and one reserved tick unaccounted at either end.
    steps = {s['clock']['step'] for s in live}
    assert len(steps) == 1, steps
    step = steps.pop()
    target = Fraction(65536, step)
    bound = Fraction((-(-65536//step)+1)*2*len(runs), fit_ticks) if fit_ticks else None
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
                     native_ms_per_tick=float(CLOCK_STEP_MS*step/0x2000))
    # PASS: the fitting time measures within ±1% including the boundary bound.
    # OVERLOADED: too little fitting time to measure; outside the gate's envelope.
    modal = (last['c3_rebased']-first['c3_rebased']) or (last['c3_excluded']-first['c3_excluded'])
    if modal or rate is None:
        status = 'FAIL' if modal else 'OVERLOADED'
    elif abs(rate/target-1) + bound <= Fraction(1, 100):
        status = 'PASS'
    elif bound > Fraction(1, 100):
        status = 'OVERLOADED'
    else:
        status = 'FAIL'
    return dict(
        status=status, world_step=step, target_rate=float(target),
        field_seconds=float(PAL_FIELD), beam_max=sorted({s['c2_beam_max'] for s in live}),
        live_samples=len(live), fields=serial, seconds=float(seconds), ticks=ticks,
        whole_rate=float(ticks/seconds), dropped=last['clock']['dropped']-first['clock']['dropped'],
        fitting_fields=fit_fields, fitting_ticks=fit_ticks, fitting_runs=runs,
        fitting_share=float(Fraction(fit_fields, serial)) if serial else None,
        rate=float(rate) if rate is not None else None,
        rate_error=float(rate/target-1) if rate is not None else None,
        rate_bound=float(bound) if bound is not None else None,
        unfit=unfit, race_clock=clock)


def rate(args, command, out, base, bases, symbols, meta):
    first_viewed = []
    def scene(name):
        # h1+$238 selected car, +$23C view code: cockpit, the tow (the first car viewed
        # from outside after the cockpit), or following another car.
        path = out/(name+'-view.bin')
        command('gdb', f'dump binary memory {path} {bases[1]+0x234:#x} {bases[1]+0x240:#x}')
        view = path.read_bytes()
        selected, code = struct.unpack_from('>I', view, 4)[0], view[8]
        if code == 0:
            return dict(scene='cockpit', view=view.hex())
        if not first_viewed:
            first_viewed.append(selected)
        return dict(scene='tow' if selected == first_viewed[0] else 'follow', view=view.hex())
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
        item['pictures'] = struct.unpack_from('>I', slave, symbols['c2_pictures'])[0]
        if getattr(args, 'scenes', False):
            item.update(scene(name))
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
    # Quit only once the results menu is up; F10 during its loading is lost.
    import f1gp
    from PIL import Image
    for _ in range(80):
        command('shot', str(out/'results.png'))
        if f1gp.showing(Image.open(out/'results.png').convert('RGB'), 'results'):
            break
        command('gdb', 'monitor fields 25')
    else:
        raise AssertionError('results menu not shown')
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
    stop, condition = 'c2_pacer', f'condition $bpnum *(unsigned short*){base+symbols["c2_in_tick"]:#x} != 0'
    if getattr(args, 'snapshot', False):
        # D1: stop after the snapshot, still before the pacer counts the tick.
        import d1_snapshot
        regions += d1_snapshot.regions(base, bases, symbols, d1_snapshot.buffers(command, base, symbols))
        stop, condition = 'd1_done', ''
    paths = [out/f'ticks-{n}.bin' for n in range(len(regions))]
    for path in paths:
        path.write_bytes(b'')
    # gdb appends each region at every tick's pacer entry and continues by itself,
    # so the whole race needs one client round trip; the epoch close stops it.
    import d1_snapshot
    appends = '\n'.join(f'append binary memory {path} {start:#x} {start+size:#x}'
                         for path, region in zip(paths, regions)
                         for start, size in d1_snapshot.pieces(region))
    command('gdb', 'delete breakpoints')
    command('gdb', f'break *{base+symbols[stop]:#x}')
    if condition:
        command('gdb', condition)
    command('gdb', f'commands $bpnum\nsilent\n{appends}\ncontinue\nend')
    if getattr(args, 'alpha', False):
        # D2: the clock and the picture's timing state after each alpha.
        import d2_alpha
        picture_regions = d2_alpha.regions(base, symbols)
        picture_paths = [out/f'pictures-{n}.bin' for n in range(len(picture_regions))]
        for path in picture_paths:
            path.write_bytes(b'')
        picture_appends = '\n'.join(f'append binary memory {path} {start:#x} {start+size:#x}'
                                     for path, (start, size) in zip(picture_paths, picture_regions))
        command('gdb', f'break *{base+symbols["d2_off"]:#x}')
        command('gdb', f'commands $bpnum\nsilent\n{picture_appends}\ncontinue\nend')
    if getattr(args, 'stage', False):
        # D3: the staged and saved inputs, the restored game memory and the snapshots.
        import d3_stage
        # D7: the track stretches the pit lane swaps with, from the start wrap pointers.
        command('gdb', f'dump binary memory {out}/track-start-h2.bin {bases[2]+0x1fab8:#x} {bases[2]+0x1fae8:#x}')
        game = d3_stage.GAME + tuple(d3_stage.swapped((out/'track-start-h2.bin').read_bytes(), bases[1]))
        stage_regions = d3_stage.regions(base, bases, symbols,
                                         d3_stage.d1.buffers(command, base, symbols), game)
        stage_paths = [out/f'stages-{n}.bin' for n in range(len(stage_regions))]
        for path in stage_paths:
            path.write_bytes(b'')
        stage_appends = '\n'.join(f'append binary memory {path} {start:#x} {start+size:#x}'
                                   for path, region in zip(stage_paths, stage_regions)
                                   for start, size in d3_stage.d1.pieces(region))
        command('gdb', f'break *{base+symbols["d3_restored"]:#x}')
        command('gdb', f'commands $bpnum\nsilent\n{stage_appends}\ncontinue\nend')
    if getattr(args, 'twin', False):
        # E3: at each twin difference, the fast picture, the blitter's chip picture
        # and the slave's clock words, appended in that order.
        fast, chip = (f'*(unsigned int*){base+symbols[n]:#x}' for n in ('e3_buffer', 'e3_chip'))
        twin = out/'twin-faults.bin'
        twin.write_bytes(b'')
        command('gdb', f'break *{base+symbols["e3_fault"]:#x}')
        command('gdb', f'commands $bpnum\nsilent\nset $e3f = {fast}\nset $e3c = {chip}\n'
                       f'append binary memory {twin} $e3f $e3f+32000\nappend binary memory {twin} $e3c $e3c+32000\n'
                       f'append binary memory {twin} {base+header[0]:#x} {base+header[1]:#x}\ncontinue\nend')
    if getattr(args, 'views', False):
        # One instruction into c2_pacer (after its move from SR), so these never share
        # an address with the tick stop of a run without snapshots.
        clock = base+symbols['c2_clock']+24
        epochs = base+symbols['c3_epochs']
        for epoch, tick, raw in VIEWS:
            for at, state in ((tick, 1), (tick+2, 0)):
                command('gdb', f'break *{base+symbols["c2_pacer"]+2:#x}')
                command('gdb', f'condition $bpnum *(unsigned short*){base+symbols["c2_in_tick"]:#x} != 0'
                               f' && *(unsigned int*){clock:#x} == {at-1} && *(unsigned int*){epochs:#x} == {epoch}')
                command('gdb', f'commands $bpnum\nsilent\nmonitor key {raw:x} {state}\ncontinue\nend')
        result['views'] = [list(v) for v in VIEWS]
        serial = f'*(unsigned int*){base+symbols["c2_serial"]:#x}'
        command('gdb', 'set $replay = 0')
        command('gdb', 'set $replay_at = 0')
        presses = {}
        for step, raw in ((2, 0x13), (5, 0x40)):
            reply = command('gdb', f'break *{base+symbols["c2_vbl"]:#x}')
            presses[step] = int(re.search(r'Breakpoint (\d+)', reply)[1])
            command('gdb', f'condition {presses[step]} $replay == {step} && {serial} >= $replay_at')
            command('gdb', f'commands {presses[step]}\nsilent\nmonitor key {raw:x} 1\nset $replay = {step+1}\n'
                           f'disable {presses[step]}\ncontinue\nend')
            command('gdb', f'disable {presses[step]}')
        steps = (('c2_pacer', 0, 'monitor key 40 1'),
                 ('c3_pause_begin', 1, f'monitor key 40 0\nset $replay_at = {serial} + {PAUSE_FIELDS}\nenable {presses[2]}'),
                 ('c3_leave_replay_start', 3, 'monitor key 13 0'),
                 ('c3_pause_begin', 4, f'set $replay_at = {serial} + {PAUSE_FIELDS}\nenable {presses[5]}'),
                 ('c3_resume', 6, 'monitor key 40 0'))
        for name, step, keys in steps:
            if name == 'c2_pacer':
                command('gdb', f'break *{base+symbols["c2_pacer"]+2:#x}')
                command('gdb', f'condition $bpnum $replay == 0 && *(unsigned short*){base+symbols["c2_in_tick"]:#x} != 0'
                               f' && *(unsigned int*){clock:#x} == {REPLAY-1} && *(unsigned int*){epochs:#x} == 1')
            else:
                command('gdb', f'break *{base+symbols[name]:#x}')
                command('gdb', f'condition $bpnum $replay == {step}')
            command('gdb', f'commands $bpnum\nsilent\n{keys}\nset $replay = {step+1}\ncontinue\nend')
        result['replay'] = REPLAY
    # The race's end closes its epoch; with the replay, its own entry and exit close one too.
    leave = 'c3_leave_race' if getattr(args, 'views', False) else 'c3_leave'
    command('gdb', f'break *{base+symbols[leave]:#x}')
    command('gdb', 'continue')
    pc = int(re.search(r'\$\d+\s*=\s*(0x[0-9a-fA-F]+)', command('gdb', 'p/x $pc'))[1], 16)
    assert pc == base+symbols[leave], hex(pc)
    # The slave's counters at the epoch close (E3's VERIFY counts are logged only after it).
    command('gdb', f'dump binary memory {out}/slave-end.bin {base:#x} {base+symbols["c2_beam_max"]+2:#x}')
    if getattr(args, 'views', False):
        steps = re.search(r'= (\d+)', command('gdb', 'p $replay'))
        if not steps or int(steps[1]) != 7:
            raise ValueError(f'replay steps incomplete: {steps and steps[1]}')
    command('gdb', 'delete breakpoints')
    if getattr(args, 'stage', False):
        # D4: the track geometry and its wrap pointers, static during the race,
        # for the segment search that places the predicted road anchor.
        import d4_camera
        result['track'] = d4_camera.dump_track(command, out, bases)
    columns = [path.read_bytes() for path in paths]
    count = len(columns[0]) // regions[0][1]
    assert count and all(len(c) == count*size for c, (_, size) in zip(columns, regions)), count
    blobs, extras = [], []
    for n in range(count):
        parts = [c[n*size:(n+1)*size] for c, (_, size) in zip(columns, regions)]
        item = tick_header(parts[0], symbols)
        item['sha256'] = hashlib.sha256(parts[1]+parts[2]).hexdigest()
        result['ticks'].append(item)
        blobs.append(b''.join(parts[:3]))
        extras.append(b''.join(parts[3:]))
    for path in paths:
        path.unlink()
    if len(regions) > 3:
        (out/'snapshots.bin.gz').write_bytes(gzip.compress(b''.join(extras), mtime=0))
        result['snapshot'] = dict(
            size=d1_snapshot.SIZE, stop=stop, regions=regions[3:],
            archive_sha256=hashlib.sha256((out/'snapshots.bin.gz').read_bytes()).hexdigest())
    if getattr(args, 'alpha', False):
        columns = [path.read_bytes() for path in picture_paths]
        count = len(columns[0]) // picture_regions[0][1]
        assert count and all(len(c) == count*size for c, (_, size) in zip(columns, picture_regions))
        data = b''.join(b''.join(c[n*size:(n+1)*size] for c, (_, size) in zip(columns, picture_regions))
                        for n in range(count))
        for path in picture_paths:
            path.unlink()
        (out/'pictures.bin.gz').write_bytes(gzip.compress(data, mtime=0))
        result['pictures'] = dict(count=count, stop='d2_off', regions=picture_regions,
                                  archive_sha256=hashlib.sha256((out/'pictures.bin.gz').read_bytes()).hexdigest())
    if getattr(args, 'stage', False):
        columns = [path.read_bytes() for path in stage_paths]
        count = len(columns[0]) // stage_regions[0][1]
        assert count and all(len(c) == count*size for c, (_, size) in zip(columns, stage_regions))
        data = b''.join(b''.join(c[n*size:(n+1)*size] for c, (_, size) in zip(columns, stage_regions))
                        for n in range(count))
        for path in stage_paths:
            path.unlink()
        (out/'stages.bin.gz').write_bytes(gzip.compress(data, mtime=0))
        result['stages'] = dict(count=count, stop='d3_restored', regions=stage_regions, game=game,
                                archive_sha256=hashlib.sha256((out/'stages.bin.gz').read_bytes()).hexdigest())
    (out/'ticks.bin.gz').write_bytes(gzip.compress(b''.join(blobs), mtime=0))
    result.update(status='PASS', record=len(blobs[0]), count=len(blobs),
                  archive_sha256=hashlib.sha256((out/'ticks.bin.gz').read_bytes()).hexdigest())
    (out/'states.json').write_text(json.dumps(result)+'\n')
