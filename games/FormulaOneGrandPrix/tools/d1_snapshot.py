#!/usr/bin/env python3
"""D1 presentation snapshots: layout, capture regions and the per-tick check.

  d1_snapshot.py CAPTURE [--out tmp/...json] [--negative]

CAPTURE is a c2_capture --states --snapshot directory. At every completed tick the
slave copies the renderer inputs mapped by A4 into cur and moves the old cur to prev.
The check rebuilds each snapshot independently from the game memory dumped at the same
stop and requires prev to be the previous tick's cur. This layout is the specification
the slave tables (d1_ranges, d1_fields) must match.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct

# Header: field number, tick, epoch, rebased fields, reconstructions, mode, draw mode.
HEADER = struct.Struct('>5I2H')
# (hunk, offset, bytes) in slave order.
RANGES = ((1, 0x224, 32),        # pose source, selected car, view code, requests, fallback
          (0, 0x3a70c, 24),      # chase flag and heading, player pointer
          (0, 0x3a7f8, 52),      # published camera and spring
          (0, 0x3a8c2, 4),       # yaw trig coefficients
          (0, 0x3a8f8, 24),      # TV and chase parameters, view height bias
          (2, 0x231d4, 20),      # horizon, view bias, viewport
          (2, 0x231a0, 2))       # covered-road flag (D6)
# (record offset, bytes) for the synthetic camera h1+$256 and the 26 cars h1+$5D6.
FIELDS = ((0x00, 56), (0x48, 4), (0x66, 2), (0x72, 2), (0x7e, 4), (0x8c, 2),
          (0x96, 2), (0xac, 2), (0xb6, 2))
RECORDS = (0x256,) + tuple(0x5d6 + i*0xc0 for i in range(26))
RECORD = sum(n for _, n in FIELDS)
SIZE = HEADER.size + sum(n for _, _, n in RANGES) + len(RECORDS)*RECORD

# Game memory dumped beside the slave state at each stop (the C5 regions cover h1+$368–1955).
GAME = ((1, 0x224, 0x316-0x224), (0, 0x3a70c, 0x3a910-0x3a70c), (2, 0x231d4, 20),
        (2, 0x231a0, 2))


def regions(base, bases, symbols):
    """Extra (start, size) regions for c5_capture.states: slave counters, buffers, game."""
    epochs = symbols['c3_epochs']
    assert symbols['c3_reconstructions'] == epochs+12 and symbols['c3_rebased'] == epochs+16
    slave = [(base+epochs, 20), (base+symbols['d1_current'], 2+2*SIZE)]
    return slave + [(bases[h]+offset, size) for h, offset, size in GAME]


def memory(parts, cars):
    """Map (hunk, offset) to bytes from the dumped game regions and the C5 car region."""
    found = [(h, offset, part) for (h, offset, _), part in zip(GAME, parts)]
    found.append((1, 0x368, cars))
    def read(h, offset, size):
        for hunk, start, part in found:
            if hunk == h and start <= offset and offset+size <= start+len(part):
                return part[offset-start:offset-start+size]
        raise KeyError(f'h{h}+{offset:05x} not captured')
    return read


def extract(read):
    """The snapshot body the slave should have written from this game memory."""
    body = b''.join(read(h, offset, size) for h, offset, size in RANGES)
    for record in RECORDS:
        body += b''.join(read(1, record+offset, size) for offset, size in FIELDS)
    return body


def split(slave):
    """(cur, prev) buffers after a snapshot: d1_current selects cur."""
    current = struct.unpack_from('>H', slave)[0]
    a, b = slave[2:2+SIZE], slave[2+SIZE:2+2*SIZE]
    assert current in (0, 1), current
    return (a, b) if current == 0 else (b, a)


def check(directory, mutate=None):
    root = Path(directory)
    meta = json.loads((root/'meta.json').read_text())
    assert meta['status'] == 'CAPTURED' and meta['quit'] == 'OK', directory
    assert 'CUSTOM2=11 ' in meta['whd_args'], meta['whd_args']
    states = meta['states']
    snap = states['snapshot']
    archive = (root/'snapshots.bin.gz').read_bytes()
    assert hashlib.sha256(archive).hexdigest() == snap['archive_sha256']
    data = bytearray(gzip.decompress(archive))
    cars_data = gzip.decompress((root/'ticks.bin.gz').read_bytes())
    sizes = [size for _, size in snap['regions']]
    record = sum(sizes)
    assert len(data) == record*len(states['ticks']) and snap['size'] == SIZE
    c5 = states['record']
    cars_at = c5 - states['ranges']['cars'][2] - states['ranges']['session'][2]
    # Each tick record starts with the slave words from c2_serial: its loop mode (1 live, 2 replay).
    symbol = lambda name: int(meta['symbols'][name], 16) if isinstance(meta['symbols'][name], str) else meta['symbols'][name]
    mode_at = symbol('c2_mode') - symbol('c2_serial')
    if mutate:
        mutate(data, sizes)
    previous, failures, kinds = None, [], dict(first=0, consecutive=0, epoch=0, vbl_during_snapshot=0)
    for n, item in enumerate(states['ticks']):
        parts, at = [], n*record
        for size in sizes:
            parts.append(bytes(data[at:at+size]))
            at += size
        counters, slave, game = parts[0], parts[1], parts[2:]
        epochs, _, _, reconstructions, rebased = struct.unpack('>5I', counters)
        cars = cars_data[n*c5+cars_at:n*c5+cars_at+states['ranges']['cars'][2]]
        cur, prev = split(slave)
        header = HEADER.unpack_from(cur)
        # A VBL may fall between the snapshot's serial read and the stop. Catch-up
        # ticks can share a field, so field numbers only never decrease.
        late = header[0] == item['serial']-1
        kinds['vbl_during_snapshot'] += late
        mode = struct.unpack_from('>H', cars_data, n*c5+mode_at)[0]
        expected = (item['serial']-late, item['tick'], epochs, rebased, reconstructions, mode, item['draw_mode'])
        if header != expected or (previous and header[0] < HEADER.unpack_from(previous)[0]):
            failures.append(dict(tick=item['tick'], header=header, expected=expected))
        if cur[HEADER.size:] != extract(memory(game, cars)):
            body = cur[HEADER.size:]
            want = extract(memory(game, cars))
            failures.append(dict(tick=item['tick'], body=[i for i, (x, y) in enumerate(zip(body, want)) if x != y][:16]))
        if previous is None:
            kinds['first'] += 1
        elif prev != previous:
            failures.append(dict(tick=item['tick'], prev='not the previous cur'))
        elif HEADER.unpack_from(prev)[2] != epochs:
            kinds['epoch'] += 1          # ticks count from 1 again in a new epoch
        elif HEADER.unpack_from(prev)[1] == item['tick']-1:
            kinds['consecutive'] += 1
        else:
            failures.append(dict(tick=item['tick'], prev='not consecutive'))
        previous = cur
    ticks = states['ticks']
    fields = [b['serial']-a['serial'] for a, b in zip(ticks, ticks[1:])]
    return dict(status='PASS' if not failures else 'FAIL', snapshots=len(ticks),
                first_tick=ticks[0]['tick'], last_tick=ticks[-1]['tick'], size=SIZE,
                record_bytes=RECORD, records=len(RECORDS), prev=kinds,
                fields_between_ticks=dict(min=min(fields), max=max(fields)),
                tick_only=sum(t['draw_mode'] == 2 for t in ticks),
                archive_sha256=snap['archive_sha256'], failures=failures[:20],
                failure_count=len(failures))


def negative(directory):
    """Each injected defect must be rejected."""
    def flip(where):
        def mutate(data, sizes):
            record = sum(sizes)
            at = 100*record + where(sizes)
            data[at] ^= 1
        return mutate
    slave = lambda sizes: sizes[0] + 2 + HEADER.size + 40      # cur or prev body byte
    camera = lambda sizes: sum(sizes[:3]) + 0x3a7fa-0x3a70c    # published pitch in game memory
    counter = lambda sizes: 3                                   # epoch counter
    results = {}
    for name, where in (('snapshot byte', slave), ('camera byte', camera), ('epoch', counter)):
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
