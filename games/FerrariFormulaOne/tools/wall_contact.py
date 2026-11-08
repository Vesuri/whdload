#!/usr/bin/env python3
"""Held wall contact (open-work: the real A1200/040 hangs): drive the player into the
right-hand wall and keep throttle and steering on, then sample every native 100 ms tick.

  wall_contact.py PROFILE        env FF1_BUILD (dir), C1_VARIANT (tag), RELEASE_WHD_ARGS
                                 (CUSTOM2=1 for performance mode, CUSTOM2=0 for the original loop)

Per tick: speed, heading, segment, longitudinal and lateral position, status, and how often
the native wall response ($6988c) and the native collision handlers ran during the tick
(gdb breakpoint hit counts). Screenshots at the first contact and every 10 ticks after it.
Output tmp/step5/wall-contact-PROFILE-TAG/result.json.
"""
from pathlib import Path
import os, sys, time, signal, json, struct, hashlib, re
sys.path.insert(0, str(Path.home() / '.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
from amigaxdev.input import Input

r = Path(__file__).resolve().parents[1]; os.chdir(r)
profile = sys.argv[1]; tag = os.environ.get('C1_VARIANT', 'candidate')
out = r / 'tmp/step5' / f'wall-contact-{profile}-{tag}'; out.mkdir(parents=True, exist_ok=True)
b = Path(os.environ.get('FF1_BUILD', str(r / 'tmp/build/fr10-production'))) / 'FerrariFormulaOne.slave'
profiles = json.loads((r / 'tmp/manifest/step3-profiles.json').read_text()); os.environ.update(profiles[profile])
whd = os.environ.get('RELEASE_WHD_ARGS', 'CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache')
perf = 'CUSTOM2=1' in whd
os.environ.update(SLAVE=str(b), WARP='1', WINDOW='none', JOY0='mouse', WHD_ARGS=whd, DETERMINISTIC='1',
                  FSUAE=os.environ.get('RELEASE_FSUAE', os.environ['FSUAE_ARM']),
                  FF1_FRAME_SENTINEL='0',
                  KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
TICKS = int(os.environ.get('WALL_TICKS', '80'))
# Native addresses (code hunk, canonical layout): the wall response and the car-contact paths.
WATCH = {'wall_6988c': 0x6988c, 'impulse_6ee00': 0x6ee00, 'impulse_6ee16': 0x6ee16}
s = Server('ff1measure', root=str(r), run_script='tools/run.sh', run_dir='tmp/run/default/.run', profile_window=False)
log = []; controls = None; report = dict(profile=profile, tag=tag, whd=whd, slave_sha256=hashlib.sha256(b.read_bytes()).hexdigest())


def save():
    (out / 'result.json').write_text(json.dumps(report, indent=1) + '\n')


try:
    g = s.boot(); controls = Input(g)

    def cmd(c):
        if c.startswith('monitor input '):
            _, _, event, state = c.split()
            controls.key(0x40, int(state)) if event == 'KEY_SPACE' else controls.button(event, int(state)); v = ''
        elif c.startswith('monitor mouse '):
            dx, dy = map(int, c.split()[2:]); controls.mouse(dx, dy); v = ''
        else:
            v = g.cmd(c, timeout=180)
        log.append(c + '\n' + v); (out / 'live.log').write_text('\n'.join(log)); return v

    def val(e): return int(cmd('p/x ' + e).split('=')[-1].strip(), 16)

    def sval(e): return int(cmd('p ' + e).split('=')[-1].strip())

    def dump(label):
        chip = int(os.environ['CHIP_KB']) * 1024
        cmd(f'dump binary memory {out.relative_to(r)}/{label}.bin 0 {chip}')
        mem = (out / (label + '.bin')).read_bytes()
        for bank, base, key in [('fast', 0x200000, 'FAST_KB'), ('slow', 0xc00000, 'SLOW_KB')]:
            size = int(os.environ.get(key, '0')) * 1024
            if size:
                cmd(f'dump binary memory {out.relative_to(r)}/{label}-{bank}.bin {base} {base + size}')
                mem += bytes(base - len(mem)) + (out / f'{label}-{bank}.bin').read_bytes()
        return mem

    for attempt in range(20):
        g.cont(); time.sleep(1); g.stop()
        mem = dump('memory'); u = lambda a: struct.unpack_from('>I', mem, a)[0]
        hits = []; at = 0
        while True:
            at = mem.find(b'FF1B7PUBLICROOT', at)
            if at < 0: break
            root = u(at - 4) * 4 + 4
            if 0 < root < len(mem) and mem[root:root + 2] == bytes.fromhex('6000'): hits.append((at, root))
            at += 1
        if hits: break
    assert len(hits) == 1, hits
    marker, root = hits[0]; table = u(root + 16) * 4
    for f in out.glob('memory*.bin'): f.unlink()
    build = json.loads((b.parent / 'build.json').read_text()); hs = build['host_symbols']
    kind = '000' if profile.startswith('a500') else 'fine'
    sy = build['payloads'][kind]['symbols']; host = marker - hs['FF1PublicMarker']; probe = host + build['payloads'][kind]['offset']
    sys.path.insert(0, str(r / 'tools'))
    from step5_b7_addresses import Addresses
    # The race hunk loads on the first race start: map after it (below).
    cmd('delete')
    cmd(f'break *{root + 0x2e6}'); cmd('condition $bpnum *(unsigned int*)$a3 == 0x22f30')
    assert 'Breakpoint' in cmd('continue')
    mem = dump('race'); native = Addresses(mem, table).map
    # Let the demo race run before mapping again: the overlay that reads the keys loads later.
    cmd('delete'); cmd(f'break *{native(0x2482a)}'); cmd('ignore $bpnum 99'); assert 'Breakpoint' in cmd('continue')
    mem = dump('race'); native = Addresses(mem, table).map
    for f in out.glob('race*.bin'): f.unlink()
    # Start the race (space at the menu), as tools/test_drive_controls.py does.
    # As tools/test_drive_controls.py key(): stop at the key read, the keyboard interrupt and
    # every field; press again if the first press is missed.
    target = native(0x23708); cmd('delete'); cmd(f'break *{target}')
    cmd(f'break *{marker - hs["FF1PublicMarker"] + hs["keyboard_start"]}'); cmd(f'break *{native(0x2482a)}')
    controls.key(0x40, 1); found = False
    for attempt in range(64):
        assert 'Breakpoint' in cmd('continue')
        if val('$pc') == target and val('$d0') & 255 == 0x40: found = True; break
        if attempt == 8: controls.key(0x40, 0)
        if attempt == 12: controls.key(0x40, 1)
    controls.key(0x40, 0)
    assert found, 'space not read'
    tick = probe + sy['FF1PresentationAfterTick'] if perf else native(0x65174)
    report.update(probe=hex(probe), tick=hex(tick), perf=perf); save()

    def advance_fields(n):
        cmd('delete'); cmd(f'break *{native(0x2482a)}'); cmd(f'ignore $bpnum {n - 1}'); assert 'Breakpoint' in cmd('continue')

    def state(label):
        d = {'label': label}
        for n, a in {'speed': 0x2275a, 'heading': 0x6a66a, 'segment': 0x6a60a, 'longitudinal': 0x6a62a,
                     'status': 0x2268e, 'countdown': 0x66f94, 'mouse_x': 0x24aa8, 'steering': 0x1c6a2}.items():
            d[n] = val(f'*(unsigned short*){native(a)}')
        d['lateral'] = sval(f'*(short*){native(0x6a61a)}')
        d['cars'] = [(val(f'*(unsigned short*){native(0x6a60a + 2 * i)}'), sval(f'*(short*){native(0x6a61a + 2 * i)}'))
                     for i in range(8)]
        if perf: d['error'] = val(f'*(unsigned int*){probe + sy["error"]}')
        return d

    # Countdown, then throttle and full right steering.
    advance_fields(150); report['ready'] = state('ready'); save()
    cmd('monitor input JOY1_2ND_BUTTON 1'); advance_fields(60); report['accelerated'] = state('accelerated')
    cmd('monitor mouse 40 0')
    rows = []; first = None
    for t in range(TICKS):
        cmd('delete')
        for n, a in WATCH.items(): cmd(f'break *{native(a)}')
        cmd(f'break *{tick}')
        n_watch = len(WATCH); counts = dict.fromkeys(WATCH, 0)
        while True:
            assert 'Breakpoint' in cmd('continue')
            pc = val('$pc')
            if pc == tick: break
            for n, a in WATCH.items():
                if pc == native(a): counts[n] += 1
        d = state(f'tick-{t}'); d.update(counts); rows.append(d)
        print(t, d['speed'], d['heading'], d['lateral'], counts, flush=True)
        if first is None and counts['wall_6988c']:
            first = t; s.handle(g, f'shot {out}/contact-{t}.png')
        elif first is not None and (t - first) % 10 == 0:
            s.handle(g, f'shot {out}/contact-{t}.png')
        if t == TICKS // 2:
            cmd('monitor mouse -40 0')                        # straighten for the second half
        report['ticks'] = rows; report['first_contact'] = first; save()
    walls = [x['wall_6988c'] for x in rows]
    report['wall_per_tick'] = {str(k): walls.count(k) for k in sorted(set(walls))}
    report['status'] = 'passed'; save()
    print('wall responses per tick', report['wall_per_tick'], 'first contact', first, flush=True)
finally:
    try:
        if controls: controls.release_all()
    finally:
        (out / 'capture.log').write_text('\n'.join(log))
        if s.g: s.g.p.kill()
        try: os.kill(int((r / 'tmp/run/default/.run/fsuae.pid').read_text()), signal.SIGKILL)
        except (ProcessLookupError, FileNotFoundError): pass
