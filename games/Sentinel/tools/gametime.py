"""tools/gametime.py SNAP...: the Sentinel's turns and the energy drain in snapshots that
tools/gametime.sh takes (`snap` of $1700:$100, the field counter $58C6E and the Sentinel's
heading $77C0, 259 bytes a field).

For each file: the fields between the Sentinel's turns, the fields its timer ($17A2, object 8's
slot) waited at 1 for the main loop to serve it, and the fields between energy units drained
($1784) until the player is absorbed (energy 0).
"""
import sys

REC = 259
TIMER, ENERGY, COUNT, HEADING = 0xa2, 0x84, 0x100, 0x102


def report(path):
    data = open(path, 'rb').read()
    recs = [data[i:i + REC] for i in range(0, len(data) - REC + 1, REC)]
    field = [r[COUNT] << 8 | r[COUNT + 1] for r in recs]
    turns, waits, drains, hit = [], [], [], None
    for i in range(1, len(recs)):
        a, b = recs[i - 1], recs[i]
        if b[TIMER] == 1 and a[TIMER] != 1:
            hit = field[i]
        if b[TIMER] > a[TIMER] and a[TIMER] <= 1 and hit is not None:
            waits.append(field[i] - hit)
            hit = None
        if b[HEADING] != a[HEADING]:
            turns.append(field[i])
        if b[ENERGY] < a[ENERGY]:
            drains.append(field[i])
        if b[ENERGY] == 0:
            break                       # the player is absorbed
    gaps = lambda v: [y - x for x, y in zip(v, v[1:])]
    print(f'{path}: {len(recs)} fields')
    print(f'  turns every {gaps(turns)} fields (the timer waited {waits})')
    print(f'  energy drained every {gaps(drains)} fields, {drains[-1] - drains[0] if drains else 0} in all')


for p in sys.argv[1:]:
    report(p)
