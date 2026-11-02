#!/usr/bin/env python3
"""B4 fresh-boot gate for release, developer, VERIFY-off and VERIFY relay-on.
Run make slave slave-developer slave-verify first. All evidence is immutable tmp/b4.
--game VARIANT runs it on an edited game directory that tools/f4_inputs.py built
(--inputs, default tmp/f4/inputs), verified against manifest/f4-inputs.json.
"""
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import time
from slave_compare import ROOT, client, loader_checks
from slave_inputs import verify
from race_profile import barto, image, locate, game_hunks
from loop_profile import report
from check_disabled import check, SOURCE


def capture(name, build, custom5, game=None, custom2=0):
    verify()
    out=ROOT/'tmp/b4'/name
    out.mkdir(parents=True,exist_ok=False)
    slave=ROOT/build/'F1GP.Slave'
    build_meta=json.loads((slave.parent/'build.json').read_text())
    digest=hashlib.sha256(slave.read_bytes()).hexdigest()
    if digest != build_meta['slave_sha256'] or build_meta['source_sha256'] != hashlib.sha256(SOURCE.read_bytes()).hexdigest():
        raise ValueError('stale build; rebuild before capturing')
    (out/'slave.bin').write_bytes(slave.read_bytes())
    sock=ROOT/'amiga/.run/f1gp.sock'
    if sock.exists():
        try:
            client('quit',quiet=True)
        except (RuntimeError,subprocess.CalledProcessError):
            pass
        sock.unlink(missing_ok=True)
    args=f'CUSTOM1=0 CUSTOM2={custom2} CUSTOM3=0 CUSTOM4=0 CUSTOM5={custom5}'
    env=dict(os.environ,AMIGA_SETUP='a1200-fast',WARP='1',DETERMINISTIC='1',
             JOY0='none',JOY1='none',SLAVE=str(slave),WHD_ARGS=args,VERIFY_EXIT='1')
    if game:
        env.update(GAME=str(game),F1GP_EDITED='1')
    log=out/'serve.log'
    with log.open('w') as f:
        proc=subprocess.Popen([sys.executable,'tools/f1gp.py','serve'],cwd=ROOT,env=env,
                              stdout=f,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+120
        while 'serving on ' not in log.read_text():
            if proc.poll() is not None or time.monotonic()>deadline:
                raise RuntimeError('server did not start: '+log.read_text()[-2000:])
            time.sleep(.2)
        route=client('quickrace',str(out/'inputs.jsonl'))
        client('gdb',f'dump binary memory {out}/fast.bin 0x200000 0xa00000')
        client('profile','50',str(out/'trace.bin'))
        t=barto.load(str(out/'trace.bin'))
        if len(t.fields)!=50:
            raise ValueError('short trace')
        (out/'chip.bin').write_bytes(t.chip)
        mem=image(t.chip,(out/'fast.bin').read_bytes(),b'')
        found=locate(mem,game_hunks())
        nxt=lambda h: struct.unpack_from('>I',mem,h-4)[0]*4+4
        h0,h2=found[0][0],found[2][0]
        meta=dict(**build_meta,custom=[0,custom2,0,0,custom5],route=route,
                  whd_args=args,hunk_bases=[h0,nxt(h0),h2,nxt(h2)],fields=50,
                  game_inputs=json.loads((ROOT/'manifest/game-inputs.json').read_text()),
                  loader_checks=loader_checks(mem,h0,h2,slave,game and game/'data/f1gp'))
        if game:
            f1gp=game/'data/f1gp'
            meta['game']=dict(path=str(game),f1gp=str(f1gp),
                              f1gp_sha256=hashlib.sha256(f1gp.read_bytes()).hexdigest())
        (out/'meta.json').write_text(json.dumps(meta,indent=2)+'\n')
        report(out/'trace.bin',out/'fast.bin')
        if custom5==0:
            result=check(out)
            if result['status']!='PASS':
                raise ValueError('disabled range mismatch')
        else:
            # Check the live relay really points into the built diagnostic body,
            # and that its tail call still targets the original game pacer.
            site=mem[h0+0x3c9d2:h0+0x3c9d8]
            target=struct.unpack_from('>I',site,2)[0]
            body=mem[target:target+6]
            displacement=struct.unpack_from('>h',body,2)[0]
            original=struct.unpack_from('>I',mem,target+2+displacement)[0]
            installed=(site[:2]==bytes.fromhex('4eb9') and target!=h0+0x1272
                       and body[:2]==bytes.fromhex('2f3a') and body[4:]==bytes.fromhex('4e75')
                       and body in slave.read_bytes() and original==h0+0x1272)
            result=dict(status='PASS' if installed else 'FAIL',relay_installed=installed)
            if not installed:
                raise ValueError('VERIFY relay not installed correctly')
        if not all(meta['loader_checks'].values()):
            raise ValueError('loader check failed')
        marker=ROOT/'amiga/.run/dh0/whdload-exit.txt'
        if marker.exists():
            raise ValueError('game already exited')
        client('tap','59')
        client('gdb','monitor fields 1000')
        client('shot',str(out/'quit.png'))
        result['quit']=marker.read_text().strip() if marker.exists() else 'MISSING'
        result['loader_checks']=meta['loader_checks']
        if result['quit']!='OK':
            result['status']='FAIL'
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        if result['status']!='PASS':
            raise ValueError('B4 case failed')
        print(name,'PASS',flush=True)
        return result
    finally:
        client('quit',quiet=True)
        proc.wait(timeout=30)


# G1: the release's options are off with "Original game" (CUSTOM2=1).
CASES = (
    ('release-off','tmp/build',0,1), ('developer-off','tmp/build-developer',0,0),
    ('verify-off','tmp/build-verify',0,0), ('verify-on','tmp/build-verify',1,0),
)


def acceptance(prefix=''):
    target = ROOT/'tmp/b4'/f'{prefix}acceptance.json'
    target.write_text(json.dumps(dict(status='INCOMPLETE'))+'\n')
    results = {}
    required = {'protection_answer', 'protection_branch', 'save_flag', 'save_directory',
                'keyboard_hook', 'keyboard_exit_key', 'keyboard_built_code', 'driver_names'}
    for name, build, custom, custom2 in CASES:
        out = ROOT/'tmp/b4'/(prefix+name)
        meta = json.loads((out/'meta.json').read_text())
        result = json.loads((out/'result.json').read_text())
        if meta['slave_sha256'] != hashlib.sha256((ROOT/build/'F1GP.Slave').read_bytes()).hexdigest():
            raise ValueError(f'{name}: current build differs from capture')
        if (meta['source_sha256'] != hashlib.sha256(SOURCE.read_bytes()).hexdigest()
                or meta['custom'] != [0,custom2,0,0,custom]
                or meta['fields'] != 50 or result['status'] != 'PASS'
                or result['quit'] != 'OK'
                or set(result['loader_checks']) != required
                or not all(result['loader_checks'].values())):
            raise ValueError(f'{name}: incomplete evidence')
        if custom == 0 and check(out)['status'] != 'PASS':
            raise ValueError(f'{name}: disabled bytes differ')
        if custom and not result.get('relay_installed'):
            raise ValueError('missing enabled relay evidence')
        results[name] = result
    subprocess.check_call([sys.executable, 'tools/test_disabled.py',
                           str(ROOT/'tmp/b4'/(prefix+'verify-off')),
                           str(ROOT/'tmp/b4'/(prefix+'verify-on'))], cwd=ROOT)
    target.write_text(json.dumps(dict(status='PASS', negative_checks=True, cases=results),indent=2)+'\n')
    print('B4 PASS')


def main():
    import argparse
    import re
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--prefix', default='', help='new evidence name prefix under tmp/b4')
    parser.add_argument('--game', help='F4: an edited variant (tools/f4_inputs.py)')
    parser.add_argument('--inputs', default='tmp/f4/inputs')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]*', args.prefix):
        parser.error('prefix must contain only letters, digits, underscores and hyphens')
    game = None
    if args.game:
        import f4_inputs
        f4_inputs.verify(args.inputs, [args.game])
        game = (ROOT/args.inputs/args.game).resolve()
    if not args.check:
        for name,build,custom,custom2 in CASES:
            capture(args.prefix+name,build,custom,game,custom2)
    acceptance(args.prefix)


if __name__=='__main__':
    main()
