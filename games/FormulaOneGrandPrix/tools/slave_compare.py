#!/usr/bin/env python3
"""B3 capture and strict comparison, with a locally padded original control.

Source amiga/env.sh. Usage:
  python3 tools/slave_compare.py capture original|rebuilt|padded green|tow|follow [fields]
  python3 tools/slave_compare.py compare
All generated files stay in tmp/b3. A comparison requires every requested window;
its nonzero exit is an acceptance failure, never an invitation to mask pixels.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
from slave_inputs import verify, ROOT, SLAVE
from race_profile import game_hunks, image, locate

OUT = ROOT/'tmp/b3'
BUILT = ROOT/'tmp/build/F1GP.Slave'

def padded():
    verify()
    b = (ROOT/SLAVE).read_bytes()
    target = BUILT.read_bytes()
    n = (len(target)-36)//4
    old = struct.unpack_from('>I', b, 28)[0]
    if len(target) != n*4+36 or n < old:
        raise ValueError('target is not a larger single-code-hunk executable')
    z = bytearray(b[:32])
    struct.pack_into('>I', z, 20, n)
    struct.pack_into('>I', z, 28, n)
    z += b[32:-4] + bytes((n-old)*4) + b[-4:]
    assert z[32:32+old*4] == b[32:-4]
    path = OUT/'padded.Slave'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(z)
    return path


def client(*args, quiet=False):
    text = subprocess.check_output([sys.executable, 'tools/f1gp.py', *args], cwd=ROOT, text=True,
                                   stderr=subprocess.DEVNULL if quiet else None)
    if text.startswith('ERROR'):
        raise RuntimeError(text.strip())
    return text


def capture(case, phase, fields):
    verify()
    dest = OUT/case/phase
    if dest.exists():
        raise ValueError(f'capture already exists: {dest}')
    dest.mkdir(parents=True)
    env = dict(os.environ, AMIGA_SETUP='a1200-fast', WARP='1', DETERMINISTIC='1',
               JOY0='none', JOY1='none')
    for key in ('SLAVE', 'WHD_ARGS', 'RACE_LEADS', 'ROUTE_SHOTS', 'RACE_KEEP_TRACES'):
        env.pop(key, None)
    env['RACE_LEADS'] = '0,0,400'
    slave = ROOT/SLAVE if case == 'original' else BUILT if case == 'rebuilt' else padded()
    if case != 'original':
        env['SLAVE'] = str(slave)
    sock = ROOT/'amiga/.run/f1gp.sock'
    if sock.exists():
        # Quit through the project server; do not terminate unidentified processes.
        try:
            client('quit', quiet=True)
        except (ConnectionError, subprocess.CalledProcessError):
            pass
        sock.unlink(missing_ok=True)
    log = dest/'serve.log'
    with log.open('w') as f:
        server = subprocess.Popen([sys.executable, 'tools/f1gp.py', 'serve'], cwd=ROOT, env=env,
                                  stdout=f, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic()+120
        while 'serving on ' not in log.read_text():
            if server.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('server did not start: '+log.read_text()[-2000:])
            time.sleep(.2)
        print(client('raceprofile', phase, str(dest), str(fields)), flush=True)
        meta = json.loads((dest/'meta.json').read_text())
        chip = (dest/'chip.bin').read_bytes()
        fast = (dest/'fast.bin').read_bytes()
        mem = image(chip, fast, b'')
        bases = locate(mem, game_hunks())
        # Follow the DOS segment chain to include the BSS hunks as well.
        h0, h2 = bases[0][0], bases[2][0]
        nxt = lambda h: struct.unpack_from('>I',mem,h-4)[0]*4+4
        meta['hunk_bases'] = [h0,nxt(h0),h2,nxt(h2)]
        meta['slave_sha256'] = hashlib.sha256(slave.read_bytes()).hexdigest()
        meta['slave_bytes'] = len(slave.read_bytes())
        meta['case'] = case
        (dest/'meta.json').write_text(json.dumps(meta,indent=2)+'\n')
    finally:
        if sock.exists():
            client('quit', quiet=True)
        server.wait(timeout=30)


def compare():
    accepted = []
    report = []
    for control in ('original', 'padded'):
        passes = True
        for phase in ('green', 'tow', 'follow'):
            a, b = OUT/control/phase/'meta.json', OUT/'rebuilt'/phase/'meta.json'
            if not a.exists() or not b.exists():
                row = dict(phase=phase, control=control, status='INCOMPLETE')
                passes = False
            else:
                x, y = json.loads(a.read_text()), json.loads(b.read_text())
                diffs = [i for i, (u, v) in enumerate(zip(x['shot_digests'], y['shot_digests'])) if u != v]
                equal_len = len(x['shot_digests']) == len(y['shot_digests']) == 500
                same_layout = x['hunk_bases'] == y['hunk_bases']
                same_route = x['route'] == y['route']
                same_anchors = x['anchors'] == y['anchors']
                ok = not diffs and equal_len and same_route and same_anchors
                if control == 'padded':
                    ok &= same_layout  # equal file size alone is not a layout control
                row = dict(phase=phase, control=control, fields=x['fields'],
                           same_layout=same_layout, same_route=same_route,
                           same_anchors=same_anchors, digest_mismatches=len(diffs),
                           first_mismatch=diffs[:1], equal_length=equal_len,
                           status='PASS' if ok else 'FAIL')
                passes &= ok
            print(json.dumps(row))
            report.append(row)
        if passes:
            accepted.append(control)
    (OUT/'comparison.json').write_text(json.dumps(dict(accepted=accepted, windows=report), indent=2)+'\n')
    return 0 if accepted else 1


if __name__ == '__main__':
    if sys.argv[1:2] == ['capture']:
        case,phase = sys.argv[2:4]
        if case not in ('original','rebuilt','padded') or phase not in ('green','tow','follow'):
            sys.exit('invalid case or phase')
        capture(case,phase,int(sys.argv[4]) if len(sys.argv)>4 else 500)
    elif sys.argv[1:] == ['compare']:
        sys.exit(compare())
    else:
        sys.exit(__doc__)
