#!/usr/bin/env python3
"""Trace the autonomous demo race: every STEP fields, the player's speed, position and
status and every car's segment and lateral position (FR10: the 1 MiB layout changes the
live demo; FASTRAM_PLAN FR4 "Live race").

  demo_trace.py PROFILE      env FF1_BUILD (dir), C1_VARIANT (tag), RELEASE_WHD_ARGS,
                             DEMO_SAMPLES (default 120), DEMO_STEP (fields, default 25),
                             DEMO_SKIP (fields before the first sample)
Output tmp/step5/demo-trace-PROFILE-TAG/result.json.
"""
from pathlib import Path
import os, sys, time, signal, json, struct, hashlib
sys.path.insert(0, str(Path.home() / '.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server

r = Path(__file__).resolve().parents[1]; os.chdir(r)
profile = sys.argv[1]; tag = os.environ.get('C1_VARIANT', 'candidate')
out = r / 'tmp/step5' / f'demo-trace-{profile}-{tag}'; out.mkdir(parents=True, exist_ok=True)
b = Path(os.environ.get('FF1_BUILD', str(r / 'tmp/build/fr10-production'))) / 'FerrariFormulaOne.slave'
profiles = json.loads((r / 'tmp/manifest/step3-profiles.json').read_text()); os.environ.update(profiles[profile])
os.environ.update(SLAVE=str(b), WARP='1', WINDOW='none', JOY0='mouse', DETERMINISTIC='1',
                  WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS', 'CUSTOM1=1 CUSTOM2=1 ConfigDelay=0'),
                  FSUAE=os.environ.get('RELEASE_FSUAE', str(r / 'tmp/step5-frame-observer-build/fs-uae')),
                  FF1_FRAME_SENTINEL='0',
                  KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
SAMPLES = int(os.environ.get('DEMO_SAMPLES', '120')); STEP = int(os.environ.get('DEMO_STEP', '25'))
s = Server('ff1measure', root=str(r), run_script='tools/run.sh', run_dir='tmp/run/default/.run', profile_window=False)
log = []; report = dict(profile=profile, tag=tag, slave_sha256=hashlib.sha256(b.read_bytes()).hexdigest())


def save(): (out / 'result.json').write_text(json.dumps(report, indent=1) + '\n')


try:
    g = s.boot()

    def cmd(c):
        v = g.cmd(c, timeout=180); log.append(c + '\n' + v); (out / 'live.log').write_text('\n'.join(log)); return v

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
    cmd('delete'); cmd(f'break *{root + 0x2e6}'); cmd('condition $bpnum *(unsigned int*)$a3 == 0x22f30')
    assert 'Breakpoint' in cmd('continue')
    sys.path.insert(0, str(r / 'tools'))
    from step5_b7_addresses import Addresses
    native = Addresses(dump('race'), table).map
    for f in out.glob('*.bin'): f.unlink()
    skip = int(os.environ.get('DEMO_SKIP', '0'))
    if skip:
        cmd('delete'); cmd(f'break *{native(0x2482a)}'); cmd(f'ignore $bpnum {skip - 1}'); assert 'Breakpoint' in cmd('continue')
    rows = []
    for i in range(SAMPLES):
        cmd('delete'); cmd(f'break *{native(0x2482a)}'); cmd(f'ignore $bpnum {STEP - 1}')
        assert 'Breakpoint' in cmd('continue')
        d = {'i': i}
        for n, a in {'speed': 0x2275a, 'segment': 0x6a60a, 'longitudinal': 0x6a62a, 'status': 0x2268e,
                     'demo': 0x1bee8, 'countdown': 0x66f94, 'heading': 0x6a66a, 'laps': 0x1bdea}.items():
            d[n] = val(f'*(unsigned short*){native(a)}')
        d['lateral'] = sval(f'*(short*){native(0x6a61a)}')
        d['cars'] = [[val(f'*(unsigned short*){native(0x6a60a + 2 * k)}'), sval(f'*(short*){native(0x6a61a + 2 * k)}')]
                     for k in range(8)]
        rows.append(d); report['rows'] = rows; save()
        print(i, d['speed'], d['segment'], d['lateral'], d['status'], d['demo'], flush=True)
    report['status'] = 'passed'; save()
    s.handle(g, f'shot {out}/end.png')
finally:
    (out / 'capture.log').write_text('\n'.join(log))
    if s.g: s.g.p.kill()
    try: os.kill(int((r / 'tmp/run/default/.run/fsuae.pid').read_text()), signal.SIGKILL)
    except (ProcessLookupError, FileNotFoundError): pass
