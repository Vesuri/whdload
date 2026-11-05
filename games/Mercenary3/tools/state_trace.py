#!/usr/bin/env python3
"""Record committed state at each main-loop head; all output belongs in tmp/.

  python3 tools/state_trace.py tmp/state/boot-a.json
  python3 tools/state_trace.py --compare tmp/state/boot-a.json tmp/state/boot-b.json

ROUTE lengths are fields. Input changes at the first loop head at or after each
cumulative boundary (including the final stop), not at exact harness fields.
Same-build repeatability is required; cross-speed lockstep belongs to A7.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

from route_profile import ROOT, ROUTE
from route_runtime import at_breakpoint, deadline, delta, output_path, session, timeouts
from amigaxdev.input import Input

LOOP_DISK = 0x5df92
LOOP = LOOP_DISK - 0x3cb0
START, END = 0x5350, 0x68000
# Provisional raw windows, not a claim about object count/layout. D4 maps them.
REGIONS = {'pose': (0x7142, 0x7162), 'clock': (0x57b0, 0x57b4),
           'objects_af36': (0xaf36, 0xb31e), 'objects_b31e': (0xb31e, 0xb706)}
WORDS = {'frames': 0x7180, 'stamp': 0x52952, 'dt': 0x52954,
         'collision': 0x6f56, 'vertb': 0x529f4}


def decode(data):
    if len(data) != END - START:
        raise RuntimeError('incomplete game-image dump')
    result = {name: data[a - START:b - START].hex() for name, (a, b) in REGIONS.items()}
    result.update({name: int.from_bytes(data[a - START:a - START + 2], 'big')
                   for name, a in WORDS.items()})
    result['image_sha256'] = hashlib.sha256(data).hexdigest()
    return result


def compare(a, b):
    """Compare every recorded field, including hashes; never silently truncate."""
    for key in ('schema', 'loop_disk_offset', 'regions', 'image_range', 'route', 'input_basis'):
        if a.get(key) != b.get(key):
            return f'incompatible trace definition: {key}'
    aa, bb = a['records'], b['records']
    if not aa or not bb:
        raise ValueError('empty trace is not repeatability evidence')
    for i, (left, right) in enumerate(zip(aa, bb)):
        fields = sorted(k for k in left.keys() | right.keys() if left.get(k) != right.get(k))
        if fields:
            return f'first differing pass {i}: ' + ', '.join(fields)
    if len(aa) != len(bb):
        return f'first differing pass {min(len(aa), len(bb))}: missing record (lengths {len(aa)}, {len(bb)})'
    return None


def run(output):
    output = output_path(output)
    if any(n <= 0 for n, _ in ROUTE) or not 0 < sum(n for n, _ in ROUTE) < 60000:
        raise ValueError('route must have positive segments totaling fewer than 60000 fields')
    boot_timeout, run_timeout = timeouts()
    records, inputs = [], []
    with session(boot_timeout) as (g, meta), deadline(run_timeout, 'committed-state route'):
        controls = Input(g, log=inputs.append)
        g.cmd(f'break *{LOOP:#x}')
        # Dump one stopped snapshot, then derive all fields from those same bytes.
        with tempfile.TemporaryDirectory(prefix='state-', dir=Path(ROOT) / 'tmp') as scratch:
            dump = Path(scratch) / 'image.bin'
            elapsed, previous, segment, boundary, held = 0, meta['anchor_state']['vertb'], 0, ROUTE[0][0], []
            while True:
                at_breakpoint(g, LOOP, run_timeout)
                dump.unlink(missing_ok=True)
                reply = g.cmd(f'dump binary memory {os.path.relpath(dump)} {START:#x} {END:#x}', timeout=run_timeout)
                if not dump.exists():
                    raise RuntimeError(f'game-image dump failed: {reply}')
                state = decode(dump.read_bytes())
                elapsed += delta(state['vertb'], previous)
                previous = state['vertb']
                records.append(dict(pass_index=len(records), field=elapsed, held=held[:], **state))
                while elapsed >= boundary and segment < len(ROUTE):
                    segment += 1
                    if segment < len(ROUTE):
                        boundary += ROUTE[segment][0]
                wanted = ROUTE[segment][1] if segment < len(ROUTE) else []
                for event in held:
                    if event not in wanted:
                        controls.button(event, False)
                for event in wanted:
                    if event not in held:
                        controls.button(event, True)
                held = wanted[:]
                if segment == len(ROUTE):
                    break
        if len(records) < 2 or delta(records[-1]['frames'], records[0]['frames']) == 0:
            raise RuntimeError('route did not advance frames')
    result = dict(meta, schema=1, loop_disk_offset=hex(LOOP_DISK),
                  regions={k: [hex(a), hex(b)] for k, (a, b) in REGIONS.items()},
                  image_range=[hex(START), hex(END)], route=ROUTE,
                  input_basis='cumulative fields from entry, rounded up to loop head',
                  run_timeout=run_timeout, records=records, input=inputs)
    with output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(f'{len(records)} loop-head records, final field {elapsed}; wrote {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('output', nargs='?', type=Path)
    parser.add_argument('--compare', nargs=2, type=Path, metavar=('A', 'B'))
    args = parser.parse_args()
    if args.compare:
        if args.output:
            parser.error('output cannot accompany --compare')
        a, b = [json.loads(p.read_text()) for p in args.compare]
        difference = compare(a, b)
        print(difference or f'identical: {len(a["records"])} committed-state records')
        return int(difference is not None)
    if not args.output:
        parser.error('output or --compare is required')
    run(args.output)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (TimeoutError, RuntimeError, ValueError, OSError) as error:
        sys.exit(f'state_trace: failed: {error}')
