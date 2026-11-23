#!/usr/bin/env python3
"""Run `bench` on a list of machines, one boot at a time, each with a deadline.

    python3 tools/matrix.py [--frames N] [--deadline S] [--build B] [--full | CELL ...]

A cell is SETUP or SETUP:WHD_ARGS (several options joined with `+`, as in
`a1200-040:CACHE+NOVBRMOVE`); without cells, the four-machine matrix below (CELLS), with
`--full` the six of FULL. Each cell boots
`tools/vroom.py serve` in its own instance (`matrix`), waits for the first demo race's green
light, runs `bench N`, takes a screenshot, and quits. It reports per cell the bench line, the
WHDLoad dumps (`.whdl_*` on DH1; the next boot moves them to `tmp/dumps/`) and the screenshot.
A cell that misses its deadline is stopped (`make stop`) and reported as such.

Output: `tmp/matrix/<time>/` with `report.txt`, one `<cell>.png` and one `<cell>.log` (the
server's output) per cell. Other run options (BUILD, SLAVE, VARIANT, ...) come from the
environment as for `make run`; `--build` sets BUILD.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
INSTANCE = 'matrix'
RUN = ROOT / 'tmp/run' / INSTANCE / '.run'
SOCK = RUN / 'vroom.sock'

# The check after a change: one machine of each CPU class, the 68040 as a real board runs it
# (instruction cache only). The full list is for one-off decisions (open-work.md, step 21).
CELLS = ['a500', 'a1200', 'a1200-030:MMU', 'a1200-040:CACHE']
FULL = CELLS + ['a1200-fast', 'a1200-040:DCACHE']


def client(*args, timeout):
    return subprocess.run([sys.executable, str(ROOT / 'tools/vroom.py'), *args], cwd=ROOT,
                          env=ENV, capture_output=True, text=True, timeout=timeout).stdout.strip()


def dumps():
    dh1 = RUN / 'dh1'
    return sorted(p.name for p in dh1.glob('.whdl_*')) if dh1.is_dir() else []


def run_cell(cell, frames, deadline, out):
    setup, _, args = cell.partition(':')
    name = cell.replace(':', '-').replace('+', '-')
    # WHD_DEFAULTS as game.conf sets it, without the CACHE its run adds on 68020 and up: a
    # cell runs exactly the options it names.
    env = dict(ENV, SETUP=setup, WHD_DEFAULTS='PRELOAD SPLASHDELAY=0 NOREQ',
               WHD_ARGS=args.replace('+', ' '), WARP='1', WINDOW='none',
               JOY0='none', DETERMINISTIC='1')
    SOCK.unlink(missing_ok=True)
    log = open(out / f'{name}.log', 'w')
    server = subprocess.Popen([sys.executable, str(ROOT / 'tools/vroom.py'), 'serve'], cwd=ROOT,
                              env=env, stdout=log, stderr=subprocess.STDOUT)
    end = time.time() + deadline
    result = 'deadline'
    try:
        while not SOCK.exists():
            if server.poll() is not None:
                return f'{cell}: the server exited ({out / (name + ".log")})', []
            if time.time() > end:
                raise subprocess.TimeoutExpired('serve', deadline)
            time.sleep(0.5)
        result = client('bench', str(frames), timeout=max(1, end - time.time()))
        client('shot', str(out / f'{name}.png'), timeout=max(1, end - time.time()))
        found = dumps()
        client('quit', timeout=30)
        server.wait(timeout=30)
    except subprocess.TimeoutExpired:
        found = dumps()
        server.kill()
        subprocess.run(['make', '-s', 'stop', f'INSTANCE={INSTANCE}'], cwd=ROOT, env=ENV,
                       capture_output=True)
        result = f'missed the {deadline} s deadline'
    finally:
        log.close()
    return f'{cell}: {result}', found


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--frames', type=int, default=500)
    ap.add_argument('--deadline', type=float, default=600, help='seconds per cell')
    ap.add_argument('--build')
    ap.add_argument('--full', action='store_true', help='the six machines of FULL')
    ap.add_argument('cells', nargs='*')
    args = ap.parse_args()
    global ENV
    ENV = dict(os.environ, INSTANCE=INSTANCE, GAME=ROOT.name)
    if args.build:
        ENV['BUILD'] = args.build
    out = ROOT / 'tmp/matrix' / time.strftime('%Y%m%d-%H%M%S')
    out.mkdir(parents=True)
    lines = []
    for cell in args.cells or (FULL if args.full else CELLS):
        line, found = run_cell(cell, args.frames, args.deadline, out)
        line += f' dumps {len(found)}' + (f' ({" ".join(found)})' if found else '')
        print(line, flush=True)
        lines.append(line)
    (out / 'report.txt').write_text('\n'.join(lines) + '\n')
    print(f'report and screenshots: {out.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
