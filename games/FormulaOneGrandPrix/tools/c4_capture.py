"""C4 input acceptance probes using real harness input, never memory writes."""
import hashlib
import json
import re
import struct


# View keys: raw key -> one-shot request bit in h1+$23E and latch bit in h0+$3A915.
VIEW_KEYS = {0x4c: 7, 0x4d: 6, 0x3d: 3, 0x4e: 4, 0x4f: 5, 0x5f: 2, 0x46: 1}
SCAN_BITS = {0x4c: 15, 0x4d: 14, 0x3d: 17, 0x4e: 12, 0x4f: 13, 0x5f: 18, 0x46: 16}
PAUSE_KEY = 0x40


def pressed(item, raw):
    """Active-low native mask h0+$18 (word) and +$1A (long) as one 48-bit value."""
    return not int(item['masks'], 16) >> SCAN_BITS[raw] & 1


def probe(command, out, base, bases, symbols, result):
    h0, h1, h2, _ = bases
    observations = result['observations']
    def read(name, address, size):
        path = out/(name+'.bin')
        command('gdb', f'dump binary memory {path} {address:#x} {address+size:#x}')
        return path.read_bytes()
    def stop(address, condition=None):
        command('gdb','delete breakpoints')
        command('gdb',f'break *{address:#x}')
        if condition:
            command('gdb',f'condition $bpnum {condition}')
        command('gdb','continue')
        pc = re.search(r'\$\d+\s*=\s*(0x[0-9a-fA-F]+)',command('gdb','p/x $pc'))
        assert pc and int(pc[1],16)==address, pc
        command('gdb','delete breakpoints')
    def snap(name, raw=0x4f):
        state = read(name+'-slave',base,symbols['c2_beam_max']+2)
        native = read(name+'-h0',h0,0x3ca00)
        view = read(name+'-view',h1+0x234,14)
        keys = read(name+'-keys',h2+0x52a,128)
        player = struct.unpack_from('>I',native,0x3a720)[0]
        controls = read(name+'-control',player+0x7f,1) if player else b''
        item = dict(name=name, ticks=struct.unpack_from('>I',state,symbols['c2_clock']+24)[0],
                    batch=struct.unpack_from('>H',state,symbols['c2_clock']+10)[0],
                    draw_mode=struct.unpack_from('>H',state,symbols['c2_draw_mode'])[0],
                    serial=struct.unpack_from('>I',state,symbols['c2_serial'])[0],
                    masks=native[0x18:0x1e].hex(), latch=native[0x3a915],
                    view=view.hex(), event=view[10], raw=raw, key=keys[raw],
                    control=controls.hex(), player=player,
                    mode=struct.unpack_from('>H',state,symbols['c2_mode'])[0],
                    suspended=struct.unpack_from('>H',state,symbols['c3_suspended'])[0],
                    pauses=struct.unpack_from('>I',state,symbols['c3_pauses'])[0],
                    buffer=dict(deferred=struct.unpack_from('>I',state,symbols['c4_deferred'])[0],
                                applied=struct.unpack_from('>I',state,symbols['c4_applied'])[0],
                                live=struct.unpack_from('>H',state,symbols['c4_live'])[0],
                                state=state[symbols['c4_keys']+raw]),
                    files={suffix:hashlib.sha256(data).hexdigest() for suffix,data in
                           (('slave',state),('h0',native),('view',view),('keys',keys))})
        if controls:
            item['files']['control']=hashlib.sha256(controls).hexdigest()
        observations.append(item)
        (out/'input.json').write_text(json.dumps(result,indent=2)+'\n')
        return item
    return read, stop, snap


def exercise(args, command, out, base, bases, symbols, meta):
    assert args.custom4 == 3 and args.route == 'quickrace'
    h0, h1, h2, _ = bases
    result = dict(status='INCOMPLETE', observations=[])
    meta['input'] = result
    read, stop, snap = probe(command, out, base, bases, symbols, result)
    # Anchor to completed world ticks, not a cross-build field count.
    stop(h0+0x3c94a, f'*(unsigned int*){base+symbols["c2_clock"]+24:#x} >= 30')
    snap('anchor')
    command('gdb','monitor key 4f 1')
    stop(h2+0x4d4)
    assert snap('held-irq')['key'] == 0xb3
    held=[]
    for n in range(5):
        stop(h0+0x3c99a)
        held.append(snap(f'held-{n}'))
    sampled = [not bool(int(x['masks'],16)&0x2000) for x in held]
    edges = [v and (n==0 or not sampled[n-1]) for n,v in enumerate(sampled)]
    assert sum(edges)==1 and [bool(x['event']&0x20) for x in held]==edges, held
    assert any(x['draw_mode']==2 for x in held), 'no catch-up tick covered'
    command('gdb','monitor key 4f 0')
    stop(h2+0x4d4)
    assert snap('release-irq')['key']==0
    stop(h0+0x3c950)
    stop(h0+0x3c99a)
    assert not snap('released')['latch']&0x20
    # The controller is sampled afresh in the native per-tick call.
    command('gdb','monitor input JOY2_RIGHT 1')
    command('gdb','monitor fields 1')
    stop(h0+0x3c956)
    right=snap('stick-right')
    assert int(right['control'],16)&8, right
    command('gdb','monitor input JOY2_RIGHT 0')
    command('gdb','monitor fields 1')
    stop(h0+0x3c956)
    neutral=snap('stick-neutral')
    assert not int(neutral['control'],16)&8, neutral
    # Stop before the diagnostic 20-field delay, after a batch finishes.
    stop(base+symbols['c2_acquire'])
    before=snap('pulse-before')
    command('gdb','monitor key 4f 1')
    stop(h2+0x4d4)
    down=snap('pulse-down')
    assert down['key']==0xb3
    command('gdb','monitor key 4f 0')
    stop(h2+0x4d4)
    up=snap('pulse-up')
    # The buffer holds the release back: the table still shows the press.
    assert up['key']==0xb3 and up['buffer']['deferred']==down['buffer']['deferred']+1, up
    # No simulation tick ran between the actual keyboard IRQ stores.
    assert before['ticks']==down['ticks']==up['ticks'], (before,down,up)
    stop(h0+0x3c950)
    scanned=snap('pulse-scan')
    stop(h0+0x3c99a)
    consumed=snap('pulse-consumer')
    # The next scan shows the held-back release; the press must act only once.
    stop(h0+0x3c950)
    released=snap('pulse-release')
    stop(h0+0x3c99a)
    after=snap('pulse-after')
    once = (released['key']==0 and int(released['masks'],16)&0x2000
            and released['buffer']['applied']==scanned['buffer']['applied']+1
            and released['ticks']==scanned['ticks']+1
            and not after['event']&0x20 and not after['latch']&0x20)
    result.update(held_view='PASS', joystick='PASS', short_pulse=(
        'PASS' if not int(scanned['masks'],16)&0x2000 and consumed['event']&0x20 and once
        else 'FAIL'))
    result['status']='PASS' if result['short_pulse']=='PASS' else 'FAIL'
    (out/'input.json').write_text(json.dumps(result,indent=2)+'\n')


def evaluate_suite(items):
    """C4 acceptance from saved suite observations; shared by capture and report."""
    checks = {}
    def taps(prefix, raw, bit, pattern, scan, view):
        # Each tap is a press and release between two scans, during the forced delay.
        down, up = items[prefix+'-down'], items[prefix+'-up']
        rows = [(items[f'{prefix}-scan-{n}'], items[f'{prefix}-view-{n}']) for n in range(len(pattern))]
        return (down['ticks'] == up['ticks'] == rows[0][0]['ticks']
                and up['buffer']['deferred'] > down['buffer']['deferred']
                and [s['ticks'] for s,_ in rows] == list(range(rows[0][0]['ticks'], rows[0][0]['ticks']+len(rows)))
                and [pressed(s, raw) for s,_ in rows] == pattern
                and [bool(v['event'] >> bit & 1) for _,v in rows] == pattern
                and not rows[-1][1]['latch'] >> bit & 1
                and all(s['mode'] == v['mode'] == scan for s,v in rows))
    for raw, bit in VIEW_KEYS.items():
        checks[f'view_{raw:02x}'] = taps(f'view-{raw:02x}', raw, bit, [True, False], 1, 1)
    checks['double_tap'] = taps('double', 0x4f, 5, [True, False, True, False], 1, 1)
    checks['replay_tap'] = taps('replay', 0x4f, 5, [True, False], 2, 2)
    begin, held, resumed, later = (items['pause-'+n] for n in ('begin','held','resumed','later'))
    # The begin snapshot is at c3_pause_begin's entry, before the suspension is counted.
    checks['pause_tap'] = (begin['pauses'] == items['pause-down']['pauses']
                           and held['pauses'] == begin['pauses']+1
                           and held['suspended'] == 1 and held['ticks'] == begin['ticks']
                           and held['key'] == 0 and held['buffer']['live'] == 0
                           and held['serial'] >= begin['serial']+250
                           and resumed['suspended'] == 0 and resumed['ticks'] > held['ticks']
                           and later['pauses'] == held['pauses'] and later['suspended'] == 0
                           and later['ticks'] > resumed['ticks'])
    return {name: 'PASS' if ok else 'FAIL' for name, ok in checks.items()}


def suite(args, command, out, base, bases, symbols, meta):
    """Every view key, a pause tap, a double tap and a replay tap, each between two scans."""
    assert args.custom4 == 3 and args.route == 'quickrace'
    h0, h1, h2, _ = bases
    result = dict(status='INCOMPLETE', suite=True, observations=[])
    meta['input'] = result
    read, stop, snap = probe(command, out, base, bases, symbols, result)
    def fields(n):
        command('gdb', f'monitor fields {n}')
    def tap_in_delay(prefix, raw, presses=1):
        # Stop at the next batch's start; the forced 20-field delay follows.
        stop(base+symbols['c2_acquire'])
        for n in range(presses):
            command('gdb', f'monitor key {raw:x} 1')
            stop(h2+0x4d4)
            if n == 0:
                snap(prefix+'-down', raw)
            command('gdb', f'monitor key {raw:x} 0')
            stop(h2+0x4d4)
        snap(prefix+'-up', raw)
    def ticks(prefix, raw, count, scan=0x3c950, view=0x3c99a):
        for n in range(count):
            stop(h0+scan)
            snap(f'{prefix}-scan-{n}', raw)
            stop(h0+view)
            snap(f'{prefix}-view-{n}', raw)
    stop(h0+0x3c94a, f'*(unsigned int*){base+symbols["c2_clock"]+24:#x} >= 30')
    snap('anchor')
    for raw in VIEW_KEYS:
        tap_in_delay(f'view-{raw:02x}', raw)
        ticks(f'view-{raw:02x}', raw, 2)
    tap_in_delay('double', 0x4f, presses=2)
    ticks('double', 0x4f, 4)
    # Pause: the tap is seen by the tick's pause check; the native wait then needs a new press.
    tap_in_delay('pause', PAUSE_KEY)
    stop(base+symbols['c3_pause_begin'])
    snap('pause-begin', PAUSE_KEY)
    fields(250)
    snap('pause-held', PAUSE_KEY)
    command('tap', f'{PAUSE_KEY:x}')
    fields(100)
    snap('pause-resumed', PAUSE_KEY)
    fields(200)
    snap('pause-later', PAUSE_KEY)
    # Replay from the pause menu, as the C2 replay probe enters it.
    command('tap', f'{PAUSE_KEY:x}')
    fields(10)
    command('tap', '13')
    stop(h0+0x3cc8e)
    snap('replay-entry')
    tap_in_delay('replay', 0x4f)
    ticks('replay', 0x4f, 2, scan=0x3cc94, view=0x3ccd2)
    items = {item['name']: item for item in result['observations']}
    result['checks'] = evaluate_suite(items)
    result['status'] = 'PASS' if all(v == 'PASS' for v in result['checks'].values()) else 'FAIL'
    (out/'input.json').write_text(json.dumps(result,indent=2)+'\n')
