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
    if args.input_suite:
        args.input = True
    if args.states and (args.modal or args.input or args.rate or args.replay or args.view
                        or args.profile or args.profile_tick or args.publish or args.shots
                        or args.route != 'quickrace'):
        raise ValueError('C5 tick-state probe requires Quick Race and no other probe options')
    if args.rate and (args.modal or args.input or args.replay or args.view or args.profile
                      or args.profile_tick or args.publish or args.custom4 != 1
                      or args.route != 'quickrace'):
        raise ValueError('C5 rate probe requires Quick Race/CUSTOM4=1 and no other probe options')
    if args.input and (args.modal or args.replay or args.view or args.profile or args.profile_tick
                       or args.publish or args.custom4 != 3 or args.route != 'quickrace'):
        raise ValueError('C4 input probe requires Quick Race/CUSTOM4=3 and no other probe options')
    verify()
    pins = runtime()
    out = scratch(args.out)
    slave = scratch(args.build) / 'F1GP.Slave'
    build = json.loads((slave.parent / 'build.json').read_text())
    if build['slave_sha256'] != sha(slave) or build['source_sha256'] != sha(SOURCE):
        raise ValueError('stale C2 build')
    symbols = {n: int(o, 16) for n, o in re.findall(
        r'^([cd][1-9]_\w+)\s+00:([0-9A-F]+)$',
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
    if args.previous:
        args.stage = True
    if args.alpha or args.stage:
        args.snapshot = True
    custom2 = (7 if args.clock_68000 else 3) | (8 if args.snapshot else 0)
    custom5 = 2 if args.previous else 0
    whd = f'CUSTOM1=1 CUSTOM2={custom2} CUSTOM3=0 CUSTOM4={args.custom4} CUSTOM5={custom5} FileLog'
    if args.setup == 'a1200-030':   # the primary target: 68030/50 without an MMU
        extra += ' --cpu=68030 --uae_mmu_model=0'
        whd += ' NOMMU'
    if args.cpu_hz:     # C5(b) one-field drawing: the same 030 with a faster clock
        if args.setup != 'a1200-030':
            raise ValueError('--cpu-hz applies to the 68030 target only')
        extra += (' --uae_cpu_speed=max --uae_cpu_cycle_exact=false --uae_cpu_memory_cycle_exact=false'
                  if args.cpu_hz < 0 else f' --uae_cpu_frequency={args.cpu_hz}')
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
        report = re.findall(r'CPU=(\d+), FPU=(\d+).*?MMU=(\d+), JIT=(\d+)',
                            (ROOT/'amiga/.run/fsuae/Cache/Logs/fs-uae.log.txt').read_text(errors='replace'))
        meta['effective'] = list(map(int, report[-1])) if report else None
        if args.setup == 'a1200-030' and (not report or meta['effective'][0] != 68030
                                          or meta['effective'][2] != 0):
            raise ValueError(f"effective CPU is not a 68030 without MMU: {meta['effective']}")
        meta['route_reply'] = command(args.route, str(out / 'route.jsonl'))
        if args.replay:
            command('gdb', 'monitor fields 400')
            command('tap', '40')
            command('gdb', 'monitor fields 10')
            command('tap', '13')
            command('shot', str(out/'replay-entry.png'))
        banks = [('chip', 0, 0x80000 if args.setup == 'a500-1.5m' else 0x200000)]
        banks += ([('slow', 0xc00000, 0xd80000)] if args.setup == 'a500-1.5m'
                  else [('fast', 0x200000, 0xa00000)] if args.setup in ('a1200-fast','a1200-030') else [])
        for name, start, end in banks:
            command('gdb', f'dump binary memory {out}/{name}.bin {start:#x} {end:#x}')
        memory = image(*((out/(name+'.bin')).read_bytes() if (out/(name+'.bin')).exists()
                         else b'' for name in ('chip','fast','slow')))
        found = locate(memory, game_hunks())
        u32 = lambda a: struct.unpack_from('>I', memory, a)[0]
        h0, h2 = found[0][0], found[2][0]
        bases = [h0, u32(h0-4)*4+4, h2, u32(h2-4)*4+4]
        if args.expect_native:
            # 68000 default: no clock hook; the native pacer keeps drawing every frame.
            if memory[h0+0x2cc3c:h0+0x2cc3e] == b'\x4e\xb9':
                raise ValueError('clock hooks installed on a native-default run')
            frames = lambda: struct.unpack('>H', (out/'frames.bin').read_bytes())[0]
            command('gdb', f'dump binary memory {out}/frames.bin {h0+0x1260:#x} {h0+0x1262:#x}')
            first = frames()
            command('gdb', 'monitor fields 500')
            command('gdb', f'dump binary memory {out}/frames.bin {h0+0x1260:#x} {h0+0x1262:#x}')
            meta['native'] = dict(fields=500, frames=(frames()-first) & 0xffff,
                                  vbl_bytes=memory[h0+0x2cc3c:h0+0x2cc42].hex())
            meta['native']['fps'] = meta['native']['frames']/10
            command('tap', '59')
            command('gdb', 'monitor fields 1000')
            marker = ROOT/'amiga/.run/dh0/whdload-exit.txt'
            meta['quit'] = marker.read_text().strip() if marker.exists() else 'MISSING'
            if meta['quit'] != 'OK':
                raise ValueError('F10 quit failed')
            meta['status'] = 'CAPTURED'
            print(json.dumps(meta['native']), flush=True)
            return
        base = u32(h0+0x2cc3e)-symbols['c2_vbl']
        if memory[h0+0x2cc3c:h0+0x2cc3e] != b'\x4e\xb9':
            raise ValueError('VBL hook absent')
        clock = base + symbols['c2_clock']
        expected_mode = 2 if args.replay else 1
        if struct.unpack_from('>H', memory, base+symbols['c2_mode'])[0] != expected_mode:
            raise ValueError('requested live/replay loop not reached')
        if args.modal or args.input or args.rate or args.states:
            if args.states:
                from c5_capture import states as exercise
            elif args.rate:
                from c5_capture import rate as exercise
            elif args.input_suite:
                from c4_capture import suite as exercise
            elif args.input:
                from c4_capture import exercise
            else:
                from c3_capture import exercise
            meta.update(hunk_bases=bases, slave_base=base, symbols=symbols)
            exercise(args, command, out, base, bases, symbols, meta)
            command('gdb', 'delete breakpoints')
            command('tap', '59')
            command('gdb', 'monitor fields 1000')
            command('shot', str(out/'quit.png'))
            marker = ROOT/'amiga/.run/dh0/whdload-exit.txt'
            meta['quit'] = marker.read_text().strip() if marker.exists() else 'MISSING'
            if meta['quit'] != 'OK':
                raise ValueError('F10 quit failed')
            meta['status'] = 'CAPTURED'
            key = 'states' if args.states else 'rate' if args.rate else 'input' if args.input else 'modal'
            print(json.dumps({k: v for k, v in meta[key].items() if k not in ('samples','ticks')},
                             indent=2), flush=True)
            return
        if args.view:
            raw = dict(rear='5f', tv='4f', front='46', cockpit='4e')[args.view]
            command('tap', raw)
            command('shot', str(out/'view-entry.png'))
        meta['view'] = args.view
        if args.views:      # the D7 schedule's presses in the race before the stop
            from c5_capture import VIEWS
            epochs = base+symbols['c3_epochs']
            meta['views'] = [list(v) for v in VIEWS if v[0] == 1 and v[1]+2 < args.ticks]
            for epoch, tick, raw in meta['views']:
                for at, state in ((tick, 1), (tick+2, 0)):
                    command('gdb', f'break *{base+symbols["c2_pacer"]+2:#x}')
                    command('gdb', f'condition $bpnum *(unsigned short*){base+symbols["c2_in_tick"]:#x} != 0'
                                   f' && *(unsigned int*){clock+24:#x} == {at-1}'
                                   f' && *(unsigned int*){epochs:#x} == {epoch}')
                    command('gdb', f'commands $bpnum\nsilent\nmonitor key {raw:x} {state}\ncontinue\nend')
        meta['profile_tick'] = args.profile_tick
        meta['profile_fields'] = args.profile
        if args.profile_tick:
            if not args.profile or not 1 < args.profile_tick < args.ticks:
                raise ValueError('profile tick must precede capture and requires a profile')
            command('gdb', f'break *{base+symbols["c2_hud_overflow"]:#x}')
            command('gdb', f'break *{base+symbols["c2_pacer"]:#x}')
            command('gdb', f'condition $bpnum *(unsigned int*){clock+24:#x} >= {args.profile_tick-1}')
            command('gdb', 'continue')
            pc = re.search(r'\$\d+\s*=\s*(0x[0-9a-fA-F]+)', command('gdb', 'p/x $pc'))
            if not pc or int(pc[1], 16) != base+symbols['c2_pacer']:
                raise ValueError('profile anchor stopped outside the pacer')
            command('gdb', f'dump binary memory {out}/profile-tick.bin {clock+24:#x} {clock+28:#x}')
            if struct.unpack('>I', (out/'profile-tick.bin').read_bytes())[0] != args.profile_tick-1:
                raise ValueError('requested profile tick not reached')
            command('gdb', 'delete breakpoints')
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
        pc = re.search(r'\$\d+\s*=\s*(0x[0-9a-fA-F]+)', command('gdb', 'p/x $pc'))
        if not pc or int(pc[1], 16) != base+stop:
            raise ValueError('capture stopped outside the requested boundary')
        parts = []
        for h, (address, size) in enumerate(zip(bases, SIZES)):
            path = out/f'h{h}.bin'
            command('gdb', f'dump binary memory {path} {address:#x} {address+size:#x}')
            parts.append(path.read_bytes())
        snapshot = b''.join(parts)
        (out/'tick.bin.gz').write_bytes(gzip.compress(snapshot, mtime=0))
        if args.publish:
            bitmap = struct.unpack_from('>I', parts[0], 0x1256)[0]
            first = struct.unpack_from('>I', parts[0], 0x124a)[0]
            if bitmap not in (first, first+32000):
                raise ValueError('publication bitmap is not a canonical buffer')
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
                                 'c2_hud_overflows','c2_background_clears',
                                 'c2_background_copies')}
        meta['hud_queue'] = {name: struct.unpack_from('>H', state, symbols[name])[0]
                             for name in ('c2_hud_count','c2_hud_high')}
        if (counters['c2_hud_overflows'] or meta['hud_queue']['c2_hud_high'] > 2048
                or counters['c2_hud_queued'] != counters['c2_hud_painted'] + meta['hud_queue']['c2_hud_count']):
            raise ValueError('HUD queue overflow or accounting mismatch')
        meta['rate_detection'] = {
            name: struct.unpack_from('>H', state, symbols[name])[0]
            for name in ('c2_native_rate', 'c2_beam_max')}
        meta['view_code'] = parts[1][0x23c]
        views = dict(rear=(0xa0,), tv=(0x80,0xc0), front=(0xb0,), cockpit=(0,))
        if args.view and meta['view_code'] not in views[args.view]:
            raise ValueError('requested view not active at capture')
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
        # One screenshot per field from the stop, each with the slave state from c2_serial
        # to d1_current (the clock, picture counters and D2 state) after it. The server's
        # shot traces one field and saves the field before it, so consecutive shots are
        # consecutive fields; an extra `monitor fields 1` would skip every other one.
        start, end = symbols['c2_serial'], symbols['d1_current']
        records = []
        for n in range(args.shots):
            command('shot', str(out/f'field-{n:03d}.png'))
            command('gdb', f'dump binary memory {out}/field.bin {base+start:#x} {base+end:#x}')
            records.append((out/'field.bin').read_bytes())
        if records:
            (out/'fields.bin.gz').write_bytes(gzip.compress(b''.join(records), mtime=0))
            (out/'field.bin').unlink()
        meta['shots'] = args.shots
        meta['shot_region'] = [start, end-start]
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
                if args.setup in ('a1200-fast','a1200-030'):
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
    parser.add_argument('--build', default='tmp/c2/build-verify')
    parser.add_argument('--input', action='store_true', help='C4 native input acceptance probe')
    parser.add_argument('--input-suite', action='store_true',
                        help='C4 view keys, pause, double tap and replay tap')
    parser.add_argument('--rate', action='store_true', help='C5(a) world-tick rate over a whole race')
    parser.add_argument('--scenes', action='store_true', help='with --rate: classify each sample by screenshot')
    parser.add_argument('--states', action='store_true', help='C5(b) state at every completed tick')
    parser.add_argument('--cpu-hz', type=int, default=0, help='68030 clock for the one-field run')
    parser.add_argument('--clock-68000', action='store_true', help='CUSTOM2 bit 2: the clock on a 68000 too')
    parser.add_argument('--alpha', action='store_true', help='with --states: D2 timing of every picture (implies --snapshot)')
    parser.add_argument('--snapshot', action='store_true', help='CUSTOM2 bit 3: D1 presentation snapshots')
    parser.add_argument('--stage', action='store_true', help='with --states: D3 staged and restored inputs of every staged picture (implies --snapshot)')
    parser.add_argument('--views', action='store_true', help='the D7 view-key schedule (plain mode: the first race before the stop)')
    parser.add_argument('--previous', action='store_true', help='CUSTOM5 bit 1: the VERIFY probe stages the previous tick (implies --stage)')
    parser.add_argument('--expect-native', action='store_true', help='check the 68000 default keeps the native pacer')
    parser.add_argument('--modal', choices=('pause','menu','replay','race','pit','pause-menu'))
    parser.add_argument('--custom4', type=int, choices=(0,1,3,5,7), default=0)
    parser.add_argument('--ticks', type=int, default=100)
    parser.add_argument('--route', choices=('quickrace','qualifying','practice'), default='quickrace')
    parser.add_argument('--setup', choices=('a1200-fast','a1200-030','a1200','a500-1.5m'),
                        default='a1200-fast')
    parser.add_argument('--ntsc', action='store_true')
    parser.add_argument('--replay', action='store_true')
    parser.add_argument('--publish', action='store_true', help='stop after painting, immediately before submission')
    parser.add_argument('--view', choices=('rear','tv','front','cockpit'), help='request a native view after the route')
    parser.add_argument('--shots', type=int, default=0, help='screenshots of this many fields after the stop')
    parser.add_argument('--profile', type=int, choices=(0,50,100), default=0)
    parser.add_argument('--profile-tick', type=int, default=0, help='anchor the profile at this tick pacer instead of route completion')
    capture(parser.parse_args())
