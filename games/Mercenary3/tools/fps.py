#!/usr/bin/env python3
"""Count route frames without instruction traces (PAL, 50 fields/s).

  SLAVE=tmp/build/Mercenary3.Slave WHD_ARGS=CUSTOM1=1 python3 tools/fps.py OUT.json
  PER_FRAME=1 python3 tools/fps.py OUT.json

AMIGA_SETUP defaults to a1200-fast. ROUTE is shared with route_profile.py.
ANCHOR=entry is the validated route origin; A1's counter anchor is still pending.
BOOT_TIMEOUT (120 seconds) covers launch, debugger attachment and entry. RUN_TIMEOUT
(180 seconds) covers the route. PER_FRAME uses publication breakpoints and reports
actual elapsed fields, including segment overshoot; it is a cadence diagnostic, not
an exact-field reference run. Existing output files are never replaced.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

import _amigaxdev  # noqa: F401
from amigaxdev import gdbserve
from amigaxdev.input import Input
from route_profile import ENTRY, FRAME, ROOT, ROUTE, SLAVE


def delta(end, start):
    return (end - start) & 0xffff


@contextmanager
def deadline(seconds, stage):
    def expired(signum, frame):
        raise TimeoutError(f'{stage} exceeded {seconds:g} host seconds')
    old = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def word(g, address):
    reply = g.cmd(f'x/1xh {address:#x}')
    match = re.search(r'^\s*0x[0-9a-f]+:\s*(0x[0-9a-f]+)\s*$', reply, re.M | re.I)
    if not match:
        raise RuntimeError(f'cannot read counter: {reply}')
    return int(match[1], 16)


def snapshot(g):
    return dict(frames=word(g, 0x7180), vertb=word(g, 0x529f4),
                stamp=word(g, 0x52952), dt=word(g, 0x52954))


def at_breakpoint(g, address, timeout):
    reply = g.cmd('continue', timeout=timeout)
    pc = g.cmd('info registers pc')
    match = re.search(r'^pc\s+0x([0-9a-f]+)', pc, re.M | re.I)
    if not match or int(match[1], 16) != address or 'Breakpoint' not in reply:
        raise RuntimeError(f'expected breakpoint was not reached: {reply}\n{pc}')


def publication_intervals(samples):
    # At Disk.1 $5E4DE, the frame increment and elapsed-field store have NOT run.
    # Thus dt at sample i describes publication i-1. Pair it with the preceding
    # stamp interval; omit the startup interval and the final unobserved store.
    cadence = []
    for i in range(2, len(samples)):
        previous = samples[i - 1]
        if delta(samples[i]['frames'], previous['frames']) != 1:
            raise RuntimeError('publication samples skipped or repeated a frame')
        dt = samples[i]['dt']
        stamp_delta = delta(samples[i]['stamp'], previous['stamp'])
        if dt != stamp_delta:
            raise RuntimeError('publication elapsed fields disagree with field stamps')
        cadence.append(dict(frame=previous['frames'], fields=dt))
    return cadence


def require_pal(settings):
    if settings.get('ntsc') != 'false':
        raise RuntimeError('fps.py requires a confirmed PAL configuration (ntsc=false)')


def machine_settings(run_dir):
    """Retain effective timing/memory settings, without machine-local file paths."""
    keys = {'cpu_model', 'mmu_model', 'fpu_model', 'cpu_frequency', 'cpu_speed',
            'cpu_compatible', 'cpu_cycle_exact', 'cpu_memory_cycle_exact',
            'cpu_data_cache', 'blitter_cycle_exact', 'chipmem_size', 'fastmem_size',
            'bogomem_size', 'chipset', 'ntsc', 'cachesize'}
    settings = {}
    config = Path(run_dir) / 'fsuae/Cache/Logs/debug.uae'
    for line in config.read_text().splitlines():
        key, sep, value = line.partition('=')
        if sep and key in keys:
            settings[key] = value
    return settings


def run(boot_timeout, run_timeout, per_frame):
    os.chdir(ROOT)
    if os.environ.get('ANCHOR', 'entry') != 'entry':
        raise ValueError('only ANCHOR=entry is validated; counter anchoring awaits A1')
    if any(n <= 0 for n, _ in ROUTE) or not 0 < sum(n for n, _ in ROUTE) < 60000:
        raise ValueError('route must have positive segments and total fewer than 60000 fields')
    os.environ.update(AMIGA_SETUP=os.environ.get('AMIGA_SETUP', 'a1200-fast'),
                      FSUAE=os.environ.get('FSUAE') or os.environ['FSUAE_ARM'],
                      WARP='1', DETERMINISTIC='1', JOY0='none')
    server = gdbserve.Server('merc3', root=ROOT, profile_window=False)
    # Retain the owned debugger even if its constructor fails during attachment.
    original_gdb, owned = gdbserve.Gdb, []

    def tracked_gdb(*args, **kwargs):
        g = original_gdb.__new__(original_gdb)
        owned.append(g)
        original_gdb.__init__(g, *args, **kwargs)
        return g

    samples, segments, inputs = [], [], []
    try:
        with deadline(boot_timeout, 'boot and entry anchor'):
            gdbserve.Gdb = tracked_gdb
            try:
                g = server.boot()
                settings = machine_settings(server.run_dir)
                require_pal(settings)
            finally:
                gdbserve.Gdb = original_gdb
            g.cmd(f'break *{ENTRY:#x}')
            at_breakpoint(g, ENTRY, boot_timeout)
            g.cmd('delete')
            start = snapshot(g)
        print('anchored at Disk.1 $4EDB0', flush=True)
        field = 0
        with deadline(run_timeout, 'route'):
            # On failure the owned emulator is terminated; do not send cleanup commands
            # to a debugger still waiting for a timed-out continue.
            controls = Input(g, log=inputs.append)
            for requested, held in ROUTE:
                for event in held:
                    controls.button(event, True)
                before = snapshot(g)
                if per_frame:
                    g.cmd(f'break *{FRAME:#x}')
                    while True:
                        at_breakpoint(g, FRAME, run_timeout)
                        now = snapshot(g)
                        elapsed = delta(now['vertb'], before['vertb'])
                        samples.append(dict(field=field + elapsed, **now))
                        if elapsed >= requested:
                            break
                    g.cmd('delete')
                else:
                    left = requested
                    while left:
                        n = min(left, 6000)
                        controls.fields(n)
                        left -= n
                    now = snapshot(g)
                    elapsed = requested
                field += elapsed
                segments.append(dict(requested_fields=requested, fields=elapsed, held=held,
                                     frames=delta(now['frames'], before['frames'])))
                for event in held:
                    controls.button(event, False)
            end = snapshot(g)
        frames = delta(end['frames'], start['frames'])
        if frames == 0:
            raise RuntimeError('route published no frames')
        cadence = publication_intervals(samples)
        return dict(setup=os.environ['AMIGA_SETUP'], whd_args=os.environ.get('WHD_ARGS', ''),
                    extra_args=os.environ.get('EXTRA_ARGS', ''),
                    slave=os.path.relpath(SLAVE, ROOT),
                    slave_sha256=hashlib.sha256(Path(SLAVE).read_bytes()).hexdigest(),
                    emulator_sha256=hashlib.sha256(Path(os.environ['FSUAE']).read_bytes()).hexdigest(),
                    whdload_sha256=hashlib.sha256(Path(os.environ['WHDLOAD_BINARY']).read_bytes()).hexdigest(),
                    machine=settings,
                    anchor='entry', entry_disk_offset='0x4edb0', per_frame=per_frame,
                    boot_timeout=boot_timeout, run_timeout=run_timeout,
                    route=ROUTE, requested_fields=sum(n for n, _ in ROUTE), fields=field,
                    frames=frames, fps=frames * 50 / field, start=start, end=end,
                    fps_basis=('counter delta / game VERTB fields at nominal PAL 50 Hz'
                               if per_frame else
                               'counter delta / route fields at nominal PAL 50 Hz'),
                    segment_overshoot_fields=field - sum(n for n, _ in ROUTE),
                    cadence=cadence, samples=samples, segments=segments, input=inputs)
    finally:
        for g in owned:
            if hasattr(g, 'p'):
                g.p.kill()
                g.p.wait(timeout=5)
        subprocess.run(['/bin/bash', '-c', '. "$FSUAE_COMMON"; fsuae_stop_previous'],
                       cwd=os.path.join(ROOT, 'amiga'), check=True, timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; choose a new name')
    boot_timeout = float(os.environ.get('BOOT_TIMEOUT', '120'))
    run_timeout = float(os.environ.get('RUN_TIMEOUT', '180'))
    if not all(0 < n < 86400 for n in (boot_timeout, run_timeout)):
        parser.error('deadlines must be positive and less than one day')
    output = args.output.resolve()
    if not output.is_relative_to(Path(ROOT) / 'tmp'):
        parser.error('generated results must be stored under tmp/')
    output.parent.mkdir(parents=True, exist_ok=True)
    result = run(boot_timeout, run_timeout, os.environ.get('PER_FRAME') == '1')
    with output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(f'{result["setup"]}: {result["frames"]} frames / {result["fields"]} fields, '
          f'{result["fps"]:.2f} fps (nominal PAL window)')
    cadence = [s['fields'] for s in result['cadence']]
    if result['per_frame']:
        print(f'cadence route overshoot: {result["segment_overshoot_fields"]} fields; '
              'input boundaries differ from the exact-field route')
    if cadence:
        print(f'{len(cadence)} complete publication intervals: '
              f'{min(cadence)}..{max(cadence)} fields/frame, '
              f'mean {sum(cadence) / len(cadence):.3f}')
    else:
        print('per-frame cadence not sampled (use PER_FRAME=1 where breakpoints work)')
    print('wrote', output)


if __name__ == '__main__':
    try:
        main()
    except (TimeoutError, RuntimeError) as error:
        sys.exit(f'fps: measurement failed: {error}')
