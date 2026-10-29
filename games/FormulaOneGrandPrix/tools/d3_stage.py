#!/usr/bin/env python3
"""D3 staged renderer inputs: layout, capture regions and the per-picture check.

  d3_stage.py CAPTURE [--out tmp/...json] [--negative]

CAPTURE is a c2_capture --states --stage (or --previous) directory. Before each staged
picture is drawn the slave saves the stage set from the game, writes the staged values
in, and after the draw writes the saved bytes back. The capture stops after every
restore. The check rebuilds the decision and the staged values from the D1 snapshots,
requires the game to hold the saved bytes again, and checks the saved bytes against an
independent snapshot: between ticks the last tick's cur, inside a tick that tick's own
snapshot taken at the pacer. This layout is the specification of d3_ranges and d3_fields.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

import d1_snapshot as d1

TICK, REPEAT = 0, 2
# (hunk, offset, bytes): track anchor, published camera without the spring,
# yaw coefficients, horizon and the two viewport words.
RANGES = ((1, 0x224, 4), (0, 0x3a7f8, 40), (0, 0x3a8c2, 4),
          (2, 0x231d4, 2), (2, 0x231e0, 2), (2, 0x231e4, 2))
# (record offset, bytes): direction; pitch; height, lateral and longitudinal; segment
# and denominator; yaw, corrected longitudinal and fraction; lap segment and world X/Z;
# steering and correction; height offset.
FIELDS = ((0x00, 2), (0x04, 2), (0x08, 6), (0x12, 6), (0x1a, 6), (0x26, 10),
          (0x48, 4), (0x8c, 2))
SIZE = sum(n for _, _, n in RANGES) + len(d1.RECORDS)*sum(n for _, n in FIELDS)
COUNTERS = ('pictures', 'staged', 'latest', 'snapped', 'debris', 'records',
            'written', 'checked', 'faults', 'check_tick')
# Game memory dumped at each stop: view state and records, camera and coefficients,
# horizon limit, horizon and viewport.
GAME = ((1, 0x224, 0x1956-0x224), (0, 0x3a7f8, 0x3a8c6-0x3a7f8), (2, 0x231cc, 28))


def snapshot_offset(h, offset):
    """Offset of a game byte in a D1 snapshot body, from D1's own layout."""
    at = 0
    for hunk, start, size in d1.RANGES:
        if hunk == h and start <= offset < start+size:
            return at + offset - start
        at += size
    raise KeyError(f'h{h}+{offset:05x} not in a D1 snapshot')


def record_offset(offset):
    at = 0
    for start, size in d1.FIELDS:
        if start <= offset < start+size:
            return at + offset - start
        at += size
    raise KeyError(f'record +{offset:02x} not in a D1 snapshot')


def regions(base, bases, symbols):
    """D2 state, c3 counters, D1 buffers, the D3 block and the game stage memory."""
    assert symbols['d3_staged'] - symbols['d3_saved'] == SIZE
    slave = [(base+symbols['c2_serial'], symbols['d1_current']-symbols['c2_serial']),
             (base+symbols['c3_epochs'], 20),
             (base+symbols['d1_current'], 2+2*d1.SIZE),
             (base+symbols['d3_pictures'], symbols['d3_staged']+SIZE-symbols['d3_pictures'])]
    return slave + [(bases[h]+offset, size) for h, offset, size in GAME]


def game_reader(parts):
    # D3 captures predate the horizon limit at h2+$231CC.
    layout = GAME if len(parts[-1]) == GAME[-1][2] else GAME[:-1] + ((2, 0x231d4, 20),)
    def read(h, offset, size):
        for (hunk, start, _), part in zip(layout, parts):
            if hunk == h and start <= offset and offset+size <= start+len(part):
                return part[offset-start:offset-start+size]
        raise KeyError(f'h{h}+{offset:05x} not captured')
    return read


def extract(read):
    """The stage set from game memory, in the slave's packed order."""
    out = b''.join(read(h, offset, size) for h, offset, size in RANGES)
    for record in d1.RECORDS:
        out += b''.join(read(1, record+offset, size) for offset, size in FIELDS)
    return out


def from_snapshot(snap, game=None):
    """The stage set from a D1 snapshot. With GAME, a record whose pose flag differs
    from the snapshot's keeps the game's bytes (held); returns (bytes, held)."""
    body = snap[d1.HEADER.size:]
    out = b''.join(body[snapshot_offset(h, offset):snapshot_offset(h, offset)+size]
                   for h, offset, size in RANGES)
    held = 0
    for n, record in enumerate(d1.RECORDS):
        at = sum(size for _, _, size in d1.RANGES) + n*d1.RECORD
        if game and (game(1, record+0x7e, 1)[0] ^ body[at+record_offset(0x7e)]) & 1:
            held += 1
            out += b''.join(game(1, record+offset, size) for offset, size in FIELDS)
            continue
        out += b''.join(body[at+record_offset(offset):at+record_offset(offset)+size]
                        for offset, size in FIELDS)
    return out, held


def check(directory, mutate=None):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    assert meta['status'] == 'CAPTURED' and meta['quit'] == 'OK', directory
    probe = 'CUSTOM5=2 ' in meta['whd_args']
    symbols = {k: int(v, 16) if isinstance(v, str) else v for k, v in meta['symbols'].items()}
    states = meta['states']
    info = states['stages']
    archive = (root/'stages.bin.gz').read_bytes()
    assert hashlib.sha256(archive).hexdigest() == info['archive_sha256']
    sizes = [size for _, size in info['regions']]
    data = bytearray(gzip.decompress(archive))
    assert len(data) == sum(sizes)*info['count']
    if mutate:
        mutate(data, sizes)
    # Each tick's own snapshot, from the D1 stops.
    snap_data = gzip.decompress((root/'snapshots.bin.gz').read_bytes())
    snap_sizes = [size for _, size in states['snapshot']['regions']]
    tick_cur = {}
    for n, item in enumerate(states['ticks']):
        at = n*sum(snap_sizes) + snap_sizes[0]
        tick_cur[item['tick']] = d1.split(snap_data[at:at+snap_sizes[1]])[0]
    at_slave = lambda name: symbols[name]-symbols['c2_serial']
    at_d3 = lambda name: symbols[name]-symbols['d3_pictures']
    camera = 'd4_predicted' in symbols
    if camera:
        import d4_camera
        model = d4_camera.Model(root, meta)
        d4_counters = ('d4_predicted', 'd4_jumps', 'd4_anchors', 'd4_held', 'd4_faults')
    outcomes, shown = {}, []
    failures, kinds, sources, differing, held_total, problem_kinds = [], {}, {}, 0, 0, {}
    previous = previous_d4 = None
    for n in range(info['count']):
        parts, at = [], n*sum(sizes)
        for size in sizes:
            parts.append(bytes(data[at:at+size]))
            at += size
        slave, counters, buffers, block, game = parts[0], parts[1], parts[2], parts[3], parts[4:]
        read = game_reader(game)
        word = lambda name: struct.unpack_from('>H', slave, at_slave(name))[0]
        ticks = struct.unpack_from('>I', slave, at_slave('c2_clock')+24)[0]   # WC_TICKS
        mode, alpha = word('c2_mode'), word('d2_alpha')
        epochs = struct.unpack_from('>I', counters)[0]
        values = dict(zip(COUNTERS, struct.unpack_from('>10I', block)))
        kind, source = (struct.unpack_from('>H', block, at_d3(name))[0] for name in ('d3_kind', 'd3_source'))
        saved = block[at_d3('d3_saved'):at_d3('d3_saved')+SIZE]
        staged = block[at_d3('d3_staged'):at_d3('d3_staged')+SIZE]
        cur, prev = d1.split(buffers)
        history = cur if kind == TICK else prev
        tick = ticks + (1 if kind == TICK else 0)
        header = d1.HEADER.unpack_from(history)
        body = history[d1.HEADER.size:]
        view = lambda b, o, s: b[snapshot_offset(1, o):snapshot_offset(1, o)+s]
        valid = (header[1] == tick-1 and header[2] == epochs and header[5] == mode
                 and all(view(body, o, s) == read(1, o, s) for o, s in ((0x234, 8), (0x23c, 1))))
        expected_source = (1 if probe else 2 if camera else 0) if alpha and valid else 0
        decision = 'latest' if not alpha else 'history' if valid else 'snapped'
        if camera:
            d4 = {name: struct.unpack_from('>I', block, at_d3(name))[0] for name in d4_counters}
            spring = struct.unpack_from('>h', block, at_d3('d4_spring'))[0]
            view = read(1, 0x23c, 1)[0]
            clamp = struct.unpack_from('>h', read(2, 0x231cc, 2))[0]
        kinds[('tick' if kind == TICK else 'repeat')] = kinds.get('tick' if kind == TICK else 'repeat', 0) + 1
        sources[decision] = sources.get(decision, 0) + 1
        problems = []
        if extract(read) != saved:
            problems.append('game not restored to the saved bytes')
        if expected_source == 1:
            want, held = from_snapshot(history, read)
            held_total += held
        elif expected_source == 2:
            camera_history = history[d1.HEADER.size+snapshot_offset(0, 0x3a7f8):]
            want, outcome = model.predict(saved, camera_history, alpha, spring, clamp, view)
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
            if outcome == 'jump':
                expected_source = 0
            else:
                shown.append((tick, alpha, staged[:54], saved[:54]))
            # The model's derived values from the tick's own camera are the game's.
            derived = bytearray(saved)
            model.derive(derived, spring, clamp, view)
            if bytes(derived[:54]) != saved[:54]:
                problems.append('derived values differ from the game')
        else:
            want = saved
        if source != expected_source:
            problems.append(('source', source, expected_source))
        if staged != want:
            problems.append(('staged', [i for i, (x, y) in enumerate(zip(staged, want)) if x != y][:8]))
        differing += staged != saved
        reference = cur if kind == REPEAT else tick_cur.get(tick)
        if reference is None:
            problems.append(('no snapshot of tick', tick))
        elif from_snapshot(reference)[0] != saved:
            problems.append(('saved differs from the snapshot', tick,
                             [i for i, (x, y) in enumerate(zip(from_snapshot(reference)[0], saved)) if x != y][:8]))
        if previous and values['staged'] != previous['staged']+1:
            problems.append(('staged count', values['staged'], previous['staged']))
        if values['pictures'] != values['staged'] + values['debris']:
            problems.append(('picture count', values))
        if values['written'] or values['faults']:
            problems.append(('VERIFY counters', values['written'], values['faults']))
        if camera:
            if d4['d4_faults']:
                problems.append(('D4 VERIFY faults', d4['d4_faults']))
            if previous_d4 and d4['d4_predicted'] != previous_d4['d4_predicted'] + (source == 2):
                problems.append(('predicted count', d4['d4_predicted'], previous_d4['d4_predicted']))
            previous_d4 = d4
        if problems:
            failures.append(dict(stop=n, tick=tick, kind=kind, problems=problems))
            for problem in problems:
                name = problem if isinstance(problem, str) else problem[0]
                problem_kinds[name] = problem_kinds.get(name, 0) + 1
        previous = values
    last = previous
    if last and not last['staged']-1 <= last['checked'] <= last['staged']:
        failures.append(dict(checked=last['checked'], staged=last['staged']))
    return dict(status='PASS' if not failures and info['count'] else 'FAIL', probe=probe,
                stops=info['count'], kinds=kinds, decisions=sources,
                staged_differs=differing, held_records=held_total,
                camera=dict(outcomes=outcomes, counters=previous_d4,
                            error=d4_camera.error(shown, tick_cur)) if camera else None,
                counters={k: v for k, v in (last or {}).items() if k != 'check_tick'},
                size=SIZE, archive_sha256=info['archive_sha256'],
                problems=problem_kinds, failures=failures[:20], failure_count=len(failures))


def symbols_offset(directory, name):
    """Offset of a slave symbol in the captured D3 block."""
    symbols = json.loads((Path(directory)/'meta.json').read_text())['symbols']
    value = lambda key: int(symbols[key], 16) if isinstance(symbols[key], str) else symbols[key]
    return value(name) - value('d3_pictures')


def negative(directory, camera=False):
    """Each injected defect must be rejected."""
    def flip(where):
        def mutate(data, sizes):
            for at in where(sizes):
                data[200*sum(sizes) + at] ^= 1
        return mutate
    game_camera = lambda sizes: [sum(sizes[:5]) + 4]          # published pitch, restored game
    staged = lambda sizes: sum(sizes[:3]) + symbols_offset(directory, 'd3_staged')
    saved = lambda sizes: sum(sizes[:3]) + symbols_offset(directory, 'd3_saved')
    staged_byte = lambda sizes: [staged(sizes) + SIZE - 100]  # staged car byte
    saved_byte = lambda sizes: [saved(sizes) + SIZE - 100]    # saved car byte
    # The same published-camera byte (third byte of world X) in both D1 buffers (cur and prev).
    snapshot = lambda sizes: [sizes[0] + sizes[1] + 2 + b*d1.SIZE + d1.HEADER.size + 56+0xb for b in (0, 1)]
    cases = [('restored camera byte', game_camera), ('staged byte', staged_byte),
             ('saved byte', saved_byte), ('snapshot byte', snapshot)]
    if camera:
        cases += [('staged yaw', lambda sizes: [staged(sizes) + 4+0x15]),
                  ('staged anchor', lambda sizes: [staged(sizes) + 2]),
                  ('staged horizon', lambda sizes: [staged(sizes) + 49])]
    results = {}
    for name, where in cases:
        results[name] = check(directory, flip(where))['status']
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture')
    parser.add_argument('--out')
    parser.add_argument('--negative', action='store_true')
    args = parser.parse_args()
    result = check(args.capture)
    if args.negative:
        result['negative'] = negative(args.capture)
        if any(v != 'FAIL' for v in result['negative'].values()):
            result['status'] = 'FAIL'
    text = json.dumps(result, indent=2)+'\n'
    if args.out:
        path = Path(args.out).resolve()
        if not path.is_relative_to(Path(__file__).resolve().parents[1]/'tmp'):
            raise ValueError('output must stay in project tmp/')
        path.write_text(text)
    print(text)
