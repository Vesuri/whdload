#!/usr/bin/env python3
"""B3 modern-KickEmu repeatability and original-reference comparisons.

Source amiga/env.sh. Usage:
  python3 tools/slave_compare.py capture original|rebuilt|padded|baseline|repeat green|tow|follow [fields]
  python3 tools/slave_compare.py compare
  python3 tools/slave_compare.py compare-original
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
    slave = ROOT/SLAVE if case == 'original' else padded() if case == 'padded' else BUILT
    if case != 'original':
        env['SLAVE'] = str(slave)
    sock = ROOT/'amiga/.run/f1gp.sock'
    if sock.exists():
        # Quit through the project server; do not terminate unidentified processes.
        try:
            client('quit', quiet=True)
        except (ConnectionError, subprocess.CalledProcessError, RuntimeError):
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
        meta['capture_tools_sha256'] = {name: hashlib.sha256((ROOT/'tools'/name).read_bytes()).hexdigest()
                                         for name in ('f1gp.py', 'race_profile.py', 'slave_compare.py')}
        meta['game_inputs'] = json.loads((ROOT/'manifest/game-inputs.json').read_text())
        meta['emulator_sha256'] = hashlib.sha256(Path(meta['fsuae']).read_bytes()).hexdigest()
        if case in ('baseline', 'repeat'):
            meta['loader_checks'] = loader_checks(mem, h0, h2, slave)
        (dest/'meta.json').write_text(json.dumps(meta,indent=2)+'\n')
    finally:
        if sock.exists():
            client('quit', quiet=True)
        server.wait(timeout=30)


def compare_original():
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
    (OUT/'original-comparison.json').write_text(json.dumps(dict(accepted=accepted, windows=report), indent=2)+'\n')
    return 0 if accepted else 1


def loader_checks(mem, h0, h2, slave):
    """Check supplied-game patches against captured RAM, including the live keyboard target."""
    checks = {}
    for name, addr, expected in (
        ('protection_answer', h0+0x982, bytes.fromhex('22116000')),
        ('protection_branch', h0+0x345c4, bytes.fromhex('4e714e71')),
        ('save_flag', h2+0x3863a, b'\xff'),
        ('save_directory', h2+0x386ae, b'saves\0'),
    ):
        checks[name] = mem[addr:addr+len(expected)] == expected
    hook = mem[h2+0x4ac:h2+0x4b2]
    target = struct.unpack_from('>I', hook, 2)[0]
    # ROR/EOR displaced instructions, CMP against keyexit, BEQ quit, RTS.
    body = mem[target:target+16]
    checks['keyboard_hook'] = hook[:2] == bytes.fromhex('4eb9') and body[:8] == bytes.fromhex('e2180a0000ffb03a')
    if checks['keyboard_hook']:
        key = target+8+struct.unpack_from('>h',body,8)[0]
        checks['keyboard_exit_key'] = mem[key] == 0x59
        checks['keyboard_built_code'] = body in slave.read_bytes()[32:-4]
    # Original loader's captured names are an independent oracle for its RNC patch.
    reference = OUT/'original/green'
    oldmeta = json.loads((reference/'meta.json').read_text())
    oldmem = image((reference/'chip.bin').read_bytes(), (reference/'fast.bin').read_bytes(), b'')
    names = struct.unpack_from('>I', mem, h0+0x91a)[0]+0x900
    oldnames = struct.unpack_from('>I', oldmem, oldmeta['hunk_bases'][0]+0x91a)[0]+0x900
    checks['driver_names'] = mem[names:names+1480] == oldmem[oldnames:oldnames+1480]
    return checks


def compare():
    report = []
    for phase in ('green', 'tow', 'follow'):
        paths = [OUT/case/phase/'meta.json' for case in ('baseline', 'repeat')]
        if not all(p.exists() for p in paths):
            row = dict(phase=phase, status='INCOMPLETE')
        else:
            a, b = [json.loads(p.read_text()) for p in paths]
            keys = ('phase', 'fields', 'setup', 'fast_kb', 'leads', 'anchors', 'route',
                    'hunk_bases', 'slave_sha256', 'slave_bytes', 'whd_args',
                    'emulator_sha256', 'capture_tools_sha256', 'game_inputs')
            different = [k for k in keys if k not in a or k not in b or a[k] != b[k]]
            count_ok = a['fields'] == b['fields'] == len(a['shot_digests']) == len(b['shot_digests']) == 500
            mismatches = sum(x != y for x,y in zip(a['shot_digests'],b['shot_digests']))
            required = {'protection_answer','protection_branch','save_flag','save_directory',
                        'keyboard_hook','keyboard_exit_key','keyboard_built_code','driver_names'}
            patches_ok = all(set(m.get('loader_checks',{})) == required and
                             all(m['loader_checks'].values()) for m in (a,b))
            ok = not different and count_ok and not mismatches and patches_ok
            row = dict(phase=phase, different_metadata=different, full_window=count_ok,
                       digest_mismatches=mismatches, loader_checks=patches_ok,
                       status='PASS' if ok else 'FAIL')
        report.append(row)
        print(json.dumps(row))
    passed = all(row['status'] == 'PASS' for row in report)
    (OUT/'comparison.json').write_text(json.dumps(dict(gate='modern-repeatability',
        status='PASS' if passed else 'FAIL', windows=report),indent=2)+'\n')
    return 0 if passed else 1


if __name__ == '__main__':
    if sys.argv[1:2] == ['capture']:
        case,phase = sys.argv[2:4]
        if case not in ('original','rebuilt','padded','baseline','repeat') or phase not in ('green','tow','follow'):
            sys.exit('invalid case or phase')
        capture(case,phase,int(sys.argv[4]) if len(sys.argv)>4 else 500)
    elif sys.argv[1:] == ['compare-original']:
        sys.exit(compare_original())
    elif sys.argv[1:] == ['compare']:
        sys.exit(compare())
    else:
        sys.exit(__doc__)
