#!/usr/bin/env python3
"""Fresh, pinned C2 tick-boundary probe. All evidence stays in tmp/.

Source amiga/env.sh; c2_capture.py OUT --custom4 3 --ticks 100
CUSTOM4=3 delays batches; 7 retains raster work in those same catch-up ticks.
These are diagnostic controls, not a performance comparison.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import sys
import time

from check_disabled import SOURCE
from machine_matrix import runtime, sha
from race_profile import game_hunks, image, locate
from slave_compare import client
from slave_inputs import ROOT, verify
from state_diff import SIZES, scratch


def capture(args):
    verify()
    pins = runtime()
    out = scratch(args.out)
    slave = ROOT / 'tmp/c2/build-verify/F1GP.Slave'
    build = json.loads((slave.parent / 'build.json').read_text())
    if build['slave_sha256'] != sha(slave) or build['source_sha256'] != sha(SOURCE):
        raise ValueError('stale C2 build')
    symbols = {n: int(o, 16) for n, o in re.findall(
        r'^(c2_\w+)\s+00:([0-9A-F]+)$',
        (slave.parent / 'F1GP.lst').read_text(errors='replace'), re.M)}
    sock = ROOT / 'amiga/.run/f1gp.sock'
    if sock.exists():
        with socket.socket(socket.AF_UNIX) as connection:
            connection.settimeout(1)
            try:
                connection.connect(str(sock))
            except ConnectionRefusedError:
                sock.unlink()
            else:
                raise RuntimeError('project server already active')
    out.mkdir(parents=True, exist_ok=False)
    extra = '--joystick_port_0_autoswitch=0'
    if args.ntsc:
        extra += ' --ntsc_mode=1'
    whd = f'CUSTOM1=1 CUSTOM2=3 CUSTOM3=0 CUSTOM4={args.custom4} CUSTOM5=0 FileLog'
    env = dict(os.environ, AMIGA_SETUP=args.setup, EXTRA_ARGS=extra,
               SLAVE=str(slave), WHD_ARGS=whd, WARP='1', DETERMINISTIC='1',
               JOY0='none', JOY1='none', VERIFY_EXIT='1', FSUAE=os.environ['FSUAE_ARM'],
               F1GP_SCREEN_Y='10' if args.ntsc else '0')
    meta = dict(status='INCOMPLETE', build=build, runtime=pins, setup=args.setup,
                extra_args=extra, whd_args=whd, route=args.route, ticks=args.ticks,
                game_inputs=json.loads((ROOT/'manifest/game-inputs.json').read_text()))
    meta_path = out / 'meta.json'
    meta_path.write_text(json.dumps(meta, indent=2) + '\n')
    shutil.copyfile(slave, out / 'slave.bin')
    shutil.copyfile(slave.parent / 'F1GP.lst', out / 'slave.lst')
    def command(*words):
        result = client(*words)
        with (out/'commands.log').open('a') as log:
            log.write('> ' + ' '.join(words) + '\n' + result + '\n')
        if any(s in result for s in ('Cannot ', 'Error', 'not supported', 'Command aborted')):
            raise RuntimeError(result)
        return result
    log = out / 'serve.log'
    with log.open('w') as stream:
        process = subprocess.Popen([sys.executable, 'tools/f1gp.py', 'serve'],
                                   cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
    ready = False
    try:
        end = time.monotonic() + 180
        while 'serving on ' not in log.read_text():
            if process.poll() is not None or time.monotonic() > end:
                raise RuntimeError('server boot failed')
            time.sleep(.2)
        ready = True
        meta['route_reply'] = command(args.route, str(out / 'route.jsonl'))
        if args.replay:
            command('gdb', 'monitor fields 400')
            command('tap', '40')
            command('gdb', 'monitor fields 10')
            command('tap', '13')
            command('shot', str(out/'replay-entry.png'))
        banks = [('chip', 0, 0x80000 if args.setup == 'a500-1.5m' else 0x200000)]
        banks += ([('slow', 0xc00000, 0xd80000)] if args.setup == 'a500-1.5m'
                  else [('fast', 0x200000, 0xa00000)] if args.setup == 'a1200-fast' else [])
        for name, start, end in banks:
            command('gdb', f'dump binary memory {out}/{name}.bin {start:#x} {end:#x}')
        memory = image(*((out/(name+'.bin')).read_bytes() if (out/(name+'.bin')).exists()
                         else b'' for name in ('chip','fast','slow')))
        found = locate(memory, game_hunks())
        u32 = lambda a: struct.unpack_from('>I', memory, a)[0]
        h0, h2 = found[0][0], found[2][0]
        bases = [h0, u32(h0-4)*4+4, h2, u32(h2-4)*4+4]
        base = u32(h0+0x2cc3e)-symbols['c2_vbl']
        if memory[h0+0x2cc3c:h0+0x2cc3e] != b'\x4e\xb9':
            raise ValueError('VBL hook absent')
        clock = base + symbols['c2_clock']
        expected_mode = 2 if args.replay else 1
        if struct.unpack_from('>H', memory, base+symbols['c2_mode'])[0] != expected_mode:
            raise ValueError('requested live/replay loop not reached')
        if args.profile:
            command('profile', str(args.profile), str(out/'trace.bin'))
            meta['trace_sha256'] = sha(out/'trace.bin')
        completed = args.ticks if args.publish else args.ticks-1
        boundary = 'publish' if args.publish else 'pacer'
        if u32(clock+24) >= completed:
            raise ValueError('requested tick already passed')
        stop = symbols['c2_submit_call' if args.publish else 'c2_pacer']
        command('gdb', f'break *{base+stop:#x}')
        # A publication can skip the requested tick when a batch straddles it.
        # Stop and reject that mismatch instead of waiting forever for equality.
        command('gdb', f'condition $bpnum *(unsigned int*){clock+24:#x} >= {completed}')
        command('gdb', f'break *{base+symbols["c2_hud_overflow"]:#x}')
        command('gdb', 'continue')
        parts = []
        for h, (address, size) in enumerate(zip(bases, SIZES)):
            path = out/f'h{h}.bin'
            command('gdb', f'dump binary memory {path} {address:#x} {address+size:#x}')
            parts.append(path.read_bytes())
        snapshot = b''.join(parts)
        (out/'tick.bin.gz').write_bytes(gzip.compress(snapshot, mtime=0))
        if args.publish:
            bitmap = struct.unpack_from('>I', parts[0], 0x1252)[0]
            command('gdb', f'dump binary memory {out}/paint.bin {bitmap:#x} {bitmap+32000:#x}')
            meta['paint_sha256'] = sha(out/'paint.bin')
        command('gdb', f'dump binary memory {out}/clock.bin {base:#x} {base+len(slave.read_bytes()):#x}')
        state = (out/'clock.bin').read_bytes()
        values = struct.unpack_from('>I4H4I', state, symbols['c2_clock'])
        last, credit, rate, phase, batch, observed, consumed, dropped, ticks = values
        serial = struct.unpack_from('>I', state, symbols['c2_serial'])[0]
        counters = {name: struct.unpack_from('>I', state, symbols[name])[0]
                    for name in ('c2_pictures','c2_dry_passes','c2_repeat_pictures',
                                 'c2_replay_pictures','c2_hud_queued','c2_hud_painted',
                                 'c2_hud_overflows')}
        meta['hud_queue'] = {name: struct.unpack_from('>H', state, symbols[name])[0]
                             for name in ('c2_hud_count','c2_hud_high')}
        if (counters['c2_hud_overflows'] or meta['hud_queue']['c2_hud_high'] > 2048
                or counters['c2_hud_queued'] != counters['c2_hud_painted'] + meta['hud_queue']['c2_hud_count']):
            raise ValueError('HUD queue overflow or accounting mismatch')
        meta['rate_detection'] = {
            name: struct.unpack_from('>H', state, symbols[name])[0]
            for name in ('c2_native_rate', 'c2_beam_max')}
        if (ticks != completed or observed != (consumed+credit+dropped)&0xffffffff
                or not 1 <= batch <= 4 or not 0 <= credit <= rate
                or rate != (60 if args.ntsc else 50)):
            raise ValueError(f'clock accounting failed: {values}')
        if struct.unpack_from('>H', state, symbols['c2_mode'])[0] != expected_mode:
            raise ValueError('left requested live/replay loop before capture')
        meta.update(replay=args.replay, boundary=boundary, hunk_bases=bases, slave_base=base, symbols=symbols,
                    clock=dict(last=last, serial=serial, credit=credit, rate=rate, phase=phase,
                               batch=batch, observed=observed, consumed=consumed,
                               dropped=dropped, completed=ticks, requested_tick=args.ticks),
                    counters=counters, tick_sha256=sha(out/'tick.bin.gz'))
        command('gdb', 'delete breakpoints')
        command('shot', str(out/'race.png'))
        command('tap', '59')
        command('gdb', 'monitor fields 1000')
        command('shot', str(out/'quit.png'))
        marker = ROOT/'amiga/.run/dh0/whdload-exit.txt'
        meta['quit'] = marker.read_text().strip() if marker.exists() else 'MISSING'
        if meta['quit'] != 'OK':
            raise ValueError('F10 quit failed')
        meta['status'] = 'CAPTURED'
        print(json.dumps(dict(clock=meta['clock'], counters=counters, quit=meta['quit'])), flush=True)
    except Exception as error:
        meta['error'] = str(error)
        if ready:
            try:
                command('shot', str(out/'failure.png'))
                command('gdb', f'dump binary memory {out}/failure-chip.bin 0 0x80000')
                if args.setup == 'a1200-fast':
                    command('gdb', f'dump binary memory {out}/failure-fast.bin 0x200000 0xa00000')
            except Exception as diagnostic_error:
                meta['diagnostic_error'] = str(diagnostic_error)
        raise
    finally:
        meta_path.write_text(json.dumps(meta, indent=2) + '\n')
        if ready:
            command('quit')
        process.wait(timeout=30)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('out')
    parser.add_argument('--custom4', type=int, choices=(0,1,3,5,7), default=0)
    parser.add_argument('--ticks', type=int, default=100)
    parser.add_argument('--route', choices=('quickrace','qualifying','practice'), default='quickrace')
    parser.add_argument('--setup', choices=('a1200-fast','a1200','a500-1.5m'), default='a1200-fast')
    parser.add_argument('--ntsc', action='store_true')
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--publish', action='store_true', help='stop after painting, immediately before submission')
    parser.add_argument('--profile', type=int, choices=(0,50), default=0)
    capture(parser.parse_args())
