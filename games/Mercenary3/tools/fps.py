#!/usr/bin/env python3
"""Count route frames without instruction traces (PAL, 50 fields/s).

  SLAVE=tmp/build/Mercenary3.Slave WHD_ARGS=CUSTOM1=1 python3 tools/fps.py OUT.json
  PER_FRAME=1 python3 tools/fps.py OUT.json

AMIGA_SETUP defaults to a1200-fast. ROUTE is shared with route_profile.py.
ANCHOR=entry is validated on the 020 and 030; the latter defaults to DETERMINISTIC=0
to avoid the deterministic directory-drive/indirect-board boot deadlock.
BOOT_TIMEOUT (120 seconds) covers launch, debugger attachment and entry. RUN_TIMEOUT
(180 seconds) covers the route. PER_FRAME uses publication breakpoints and reports
actual elapsed fields, including segment overshoot; it is a cadence diagnostic, not
an exact-field reference run. Existing output files are never replaced.
"""
import argparse
import json
import os
from pathlib import Path
import sys

import _amigaxdev  # noqa: F401
from amigaxdev.input import Input
from route_profile import FRAME, ROUTE
from route_runtime import (at_breakpoint, deadline, delta, output_path, require_pal,
                           session, snapshot, timeouts, word)


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


def run(boot_timeout, run_timeout, per_frame):
    if any(n <= 0 for n, _ in ROUTE) or not 0 < sum(n for n, _ in ROUTE) < 60000:
        raise ValueError('route must have positive segments and total fewer than 60000 fields')
    samples, segments, inputs = [], [], []
    with session(boot_timeout) as (g, meta):
        if meta['frame_counter'] == 'logic only (P1 release)':
            raise RuntimeError('P1 frame measurements require the VERIFY build')
        start = snapshot(g)
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
        if meta['frame_counter'] == 'P1 publications':
            # P1 restores the game's logic dt/stamp after presentation frames.
            # Publication breakpoints still observe every displayed frame.
            cadence = []
            for previous, current in zip(samples, samples[1:]):
                if delta(current['frames'], previous['frames']) != 1:
                    raise RuntimeError('publication samples skipped or repeated a frame')
                cadence.append(dict(frame=current['frames'],
                                    fields=delta(current['vertb'], previous['vertb'])))
        else:
            cadence = publication_intervals(samples)
        return dict(meta, per_frame=per_frame, run_timeout=run_timeout,
                    route=ROUTE, requested_fields=sum(n for n, _ in ROUTE), fields=field,
                    frames=frames, fps=frames * 50 / field, start=start, end=end,
                    fps_basis=('counter delta / game VERTB fields at nominal PAL 50 Hz'
                               if per_frame else
                               'counter delta / route fields at nominal PAL 50 Hz'),
                    segment_overshoot_fields=field - sum(n for n, _ in ROUTE),
                    cadence=cadence, samples=samples, segments=segments, input=inputs)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    boot_timeout, run_timeout = timeouts()
    output = output_path(args.output)
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
    except (TimeoutError, RuntimeError, ValueError) as error:
        sys.exit(f'fps: measurement failed: {error}')
