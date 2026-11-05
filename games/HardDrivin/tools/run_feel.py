"""Run the plan step F matrix: run_feel.py ROOT --profile P --custom1 0|1|2 [--slow N] [--jobs N] [NAME...]

Captures every step C manoeuvre (build_feel.PLANS, or the NAMEs) into
tmp/prof/ROOT/NAME with tools/capture_feel.py, N emulators at a time (default
4), each under its own INSTANCE. Build the slaves first with build_feel.py.
Measure with tools/arcade/amiga_feel.py report. Run from the game directory.
"""
import argparse
import os
import queue
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_feel import PLANS   # noqa: E402

HERE = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('root')
    p.add_argument('--profile', default='a500')
    p.add_argument('--custom1', type=int, choices=(0, 1, 2), required=True)
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--slow', type=int, default=0)
    p.add_argument('--custom4', type=int, default=0, help='arcade brake: 0 full, 1 soft')
    p.add_argument('--prefix', default='feel-')
    p.add_argument('--tag', default='feel', help='INSTANCE prefix; distinct per concurrent matrix')
    p.add_argument('names', nargs='*')
    a = p.parse_args()
    names = a.names or list(PLANS)
    assert all(n in PLANS for n in names)
    (HERE / 'tmp/prof' / a.root).mkdir(parents=True, exist_ok=True)

    free = queue.Queue()
    for k in range(a.jobs):
        free.put('%s%d' % (a.tag, k))

    def one(name):
        instance = free.get()     # never two runs on one instance at once
        try:
            env = dict(os.environ, INSTANCE=instance)
            log = HERE / 'tmp/prof' / a.root / (name + '.log')
            with open(log, 'w') as f:
                r = subprocess.run([sys.executable, str(HERE / 'tools/capture_feel.py'),
                                    'tmp/prof/%s/%s' % (a.root, name), '--plan', name, '--profile', a.profile,
                                    '--custom1', str(a.custom1), '--custom4', str(a.custom4), '--slow', str(a.slow), '--prefix', a.prefix], cwd=HERE, env=env, stdout=f,
                                   stderr=subprocess.STDOUT)
        finally:
            free.put(instance)
        last = log.read_text().strip().splitlines()[-1:] or ['']
        print('%s: %s%s' % (name, last[0], '' if r.returncode == 0 else ' (exit %d)' % r.returncode), flush=True)

    with ThreadPoolExecutor(a.jobs) as pool:
        list(pool.map(one, names))


if __name__ == '__main__':
    main()
