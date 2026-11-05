#!/usr/bin/env python3
"""B3 real-input F10 check; run after sourcing amiga/env.sh.

A fresh deterministic boot uses CUSTOM1=1, enters Quick Race, presses F10 and
requires WHDLoad to return successfully. Evidence stays in immutable tmp/b3/quit.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
from slave_compare import client, ROOT, BUILT
from slave_inputs import verify

verify()
out = ROOT/'tmp/b3/quit'
out.mkdir(parents=True, exist_ok=False)
sock = ROOT/'amiga/.run/f1gp.sock'
if sock.exists():
    try:
        client('quit', quiet=True)
    except (RuntimeError, subprocess.CalledProcessError):
        pass
    sock.unlink(missing_ok=True)
env = dict(os.environ, AMIGA_SETUP='a1200-fast', WARP='1', DETERMINISTIC='1',
           JOY0='none', JOY1='none', SLAVE=str(BUILT), VERIFY_EXIT='1', WHD_ARGS='CUSTOM1=1')
log = out/'serve.log'
with log.open('w') as f:
    server = subprocess.Popen([sys.executable, 'tools/f1gp.py', 'serve'], cwd=ROOT,
                              env=env, stdout=f, stderr=subprocess.STDOUT)
try:
    deadline = time.monotonic()+120
    while 'serving on ' not in log.read_text():
        if server.poll() is not None or time.monotonic() > deadline:
            raise RuntimeError(log.read_text())
        time.sleep(.2)
    result = dict(route=client('quickrace'),
                  slave_sha256=hashlib.sha256(BUILT.read_bytes()).hexdigest(),
                  whd_args=env['WHD_ARGS'])
    marker = ROOT/'amiga/.run/dh0/whdload-exit.txt'
    if marker.exists():
        raise RuntimeError('WHDLoad already returned before F10')
    result['marker_absent_before_key'] = True
    result['press'] = client('gdb', 'monitor key 59 1')
    result['advance'] = client('gdb', 'monitor fields 1000')
    result['release'] = client('gdb', 'monitor key 59 0')
    client('shot', str(out/'after-f10.png'))
    result['exit_status'] = marker.read_text().strip() if marker.exists() else 'MISSING'
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    if result['exit_status'] != 'OK':
        raise RuntimeError('WHDLoad did not return cleanly')
finally:
    client('quit', quiet=True)
    server.wait(timeout=30)
