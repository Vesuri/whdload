#!/usr/bin/env python3
"""Record a passenger flight pass by pass, and compare two recordings.

A passenger flight replays recorded joystick input keyed to the logic-pass counter
($7180, see internals P3), so the ship's course is a function of the pass number alone:
two builds that keep the logic native must give the same pose at every pass, whatever
they draw in between.

  SAVES=tmp/replay/saves SLOT=1 python3 tools/replay_trace.py OUT.json
  python3 tools/replay_trace.py --compare A.json B.json

The run loads save SLOT (HELP, F2, digit, Return), boards with B, then stops at every
main-loop head (Disk.1 $5DF92) and records the pass counter, the replay flag $70A2 and
list pointer $709A, the pose $7142..$7161 and the VERTB count. It ends PASSES_AFTER
passes after the replay flag clears (the landing), or after MAX_FIELDS fields, and saves
SHOTS screenshots of the last fields (OUT stem + .png). AMIGA_SETUP, SLAVE and WHD_ARGS
work as in the route tools; SAVES is the game.sh hook. DUMP_PASSES=141,142 also writes
chip RAM and, with a VERIFY slave, the slave's expansion memory at those loop heads
(OUT stem + -pass141-chip.bin, -exp.bin), to find the first state that differs.
"""
import argparse
import io
import json
import os
from pathlib import Path
import re

from route_profile import SLAVE, slave_code
from route_runtime import at_breakpoint, deadline, delta, output_path, session, timeouts, word
from amigaxdev.input import Input
from amigaxdev import barto
from PIL import Image

LOOP = 0x5df92 - 0x3cb0
DIGITS = [0x0a, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09]


def block(g, address, words):
    reply = g.cmd(f'x/{words}xh {address:#x}')
    values = [int(v, 16) for line in reply.splitlines() if ':' in line
              for v in re.findall(r'0x[0-9a-f]+', line.split(':', 1)[1], re.I)]
    if len(values) != words:
        raise RuntimeError(f'cannot read {address:#x}: {reply}')
    return values


def board(c, slot):
    """From the game entry: load save SLOT (HELP, F2, digit, Return), then board with B."""
    def key(code, settle):
        c.key(code, True)
        c.fields(5)
        c.key(code, False)
        c.fields(settle)
    c.fields(175)
    for code in (0x5f, 0x51, DIGITS[slot], 0x44):
        key(code, 100)
    key(0x35, 40)


def run(output):
    output = output_path(output)
    slot = int(os.environ.get('SLOT', '1'))
    after = int(os.environ.get('PASSES_AFTER', '40'))
    limit = int(os.environ.get('MAX_FIELDS', '12000'))
    boot_timeout, run_timeout = timeouts()
    records = []
    with session(boot_timeout) as (g, meta), deadline(run_timeout, 'passenger flight'):
        board(Input(g), slot)
        g.cmd(f'break *{LOOP:#x}')
        counter = getattr(g, 'publication_counter', None)
        dumps = {int(n) for n in os.environ.get('DUMP_PASSES', '').split(',') if n}
        expmem = None
        if dumps and counter is not None:
            code = slave_code(SLAVE)
            base = counter - (code.index(b'M3PUB001') + 8)
            expmem = (word(g, base + 0x20) << 16) | word(g, base + 0x22)
            expsize = -int.from_bytes(code[0x20:0x24], 'big', signed=True)
        start = previous = word(g, 0x529f4)
        field, seen, landed = 0, False, None
        while True:
            at_breakpoint(g, LOOP, run_timeout)
            vertb = word(g, 0x529f4)
            field += delta(vertb, previous)
            previous = vertb
            replay = word(g, 0x70a2)
            pointer = block(g, 0x709a, 2)
            record = dict(field=field, passes=word(g, 0x7180), replay=replay,
                          pointer=(pointer[0] << 16) | pointer[1], pose=block(g, 0x7142, 16))
            if counter is not None:
                record['published'] = word(g, counter)
            records.append(record)
            if record['passes'] in dumps and replay:
                dumps.discard(record['passes'])
                stem = f'{output.with_suffix("")}-pass{record["passes"]}'
                g.cmd(f'dump binary memory {os.path.relpath(stem)}-chip.bin 0 0x80000', timeout=run_timeout)
                if expmem:
                    g.cmd(f'dump binary memory {os.path.relpath(stem)}-exp.bin {expmem:#x} '
                          f'{expmem + expsize:#x}', timeout=run_timeout)
            seen = seen or bool(replay)
            if seen and not replay and landed is None:
                landed = len(records) - 1
            if landed is not None and len(records) - 1 - landed >= after or field >= limit:
                break
        g.cmd('delete')
        shots = int(os.environ.get('SHOTS', '2'))
        if shots:
            path = output.with_suffix('.bin')
            g.cmd(f'monitor profile {shots} "" "{path}"', timeout=run_timeout)
            fields = barto.load(str(path)).fields
            path.unlink()
            Image.open(io.BytesIO(fields[-1].shot)).convert('RGB').save(output.with_suffix('.png'))
    if not seen:
        raise RuntimeError('the replay flag $70A2 never set: no passenger flight')
    result = dict(meta, schema=1, slot=slot, loop_disk_offset='0x5df92', start_vertb=start,
                  landed_pass=landed, records=records)
    with output.open('x') as f:
        json.dump(result, f)
        f.write('\n')
    replayed = [r for r in records if r['replay']]
    print(f'{len(records)} passes, {len(replayed)} replayed, landing at pass record {landed}, '
          f'field {records[landed]["field"] if landed is not None else "-"}; wrote {output}')


def compare(a, b):
    """Compare replayed passes by pass counter; return a difference or None."""
    def by_pass(trace):
        return {r['passes']: r for r in trace['records'] if r['replay']}
    pa, pb = by_pass(a), by_pass(b)
    common = sorted(set(pa) & set(pb))
    if not common:
        return 'no common replayed passes'
    for n in common:
        ra, rb = pa[n], pb[n]
        if ra['pose'] != rb['pose'] or ra['pointer'] != rb['pointer']:
            return (f'first differing pass {n} (fields {ra["field"]}, {rb["field"]}):\n'
                    f'  pose {" ".join(f"{v:04x}" for v in ra["pose"])} list {ra["pointer"]:#x}\n'
                    f'  pose {" ".join(f"{v:04x}" for v in rb["pose"])} list {rb["pointer"]:#x}')
    if set(pa) != set(pb):
        return f'replayed passes differ: {len(pa)} and {len(pb)} ({min(pa)}..{max(pa)}, {min(pb)}..{max(pb)})'
    last = [t['records'][t['landed_pass']]['pose'] if t['landed_pass'] is not None else None
            for t in (a, b)]
    if last[0] != last[1]:
        return 'replays equal, landing poses differ'
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', nargs='?', type=Path)
    parser.add_argument('--compare', nargs=2, type=Path, metavar=('A', 'B'))
    args = parser.parse_args()
    if args.compare:
        a, b = [json.loads(p.read_text()) for p in args.compare]
        difference = compare(a, b)
        n = len([r for r in a['records'] if r['replay']])
        print(difference or f'identical: {n} replayed passes and the landing pose')
        return int(difference is not None)
    if not args.output:
        parser.error('output or --compare is required')
    run(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
