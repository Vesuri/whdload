#!/usr/bin/env python3
"""Can each depth-list entry be paired with its source's entry one tick earlier?
(docs/open-work.md, "Frames between ticks", step 1)

    python3 tools/pairs.py DUMP [TICKS]

DUMP is a chip dump at the main loop's top (tools/callwrites.py `capture`). The loop's calls
run in Unicorn as in tools/callwrites.py, TICKS passes (default 400, or until the game
leaves the loop). Code hooks at the simulation's depth-list writers record each entry with
its source. The writers, as `Disk.1` offsets:
- the particles' dot, dot and ground dot, and shard tails ($25252, $252c2, $25366);
- the objects' tail ($26d08);
- the attractor's lightning ($27c84);
- the ship's store ($2b250).
The renderer's tile objects are left out: the renderer makes them from the grid at its
camera.

A source on tick N pairs with tick N-1's source in the same slot when the record the
dispatcher finds on tick N ($25242 for the particles, $26cde for the objects) is the record
at that source's tail on tick N-1, so that nothing changed it between. A frame between the
two ticks then blends the two entries word by word. Reported per writer:
- pairs, and of them the ones shown on both ticks;
- the unpaired: spawned after the dispatcher, or changed after its tail (and in which
  record fields), found from the records at the end of tick N-1;
- the sources of tick N-1 with none on tick N (removed);
- in the pairs: a changed writer, plotter, model or bucket, how far the positions move a tick
  (screen pixels for the dots, units for the rest), and how far the matrices' words move.
The camera's step a tick ($107e) is reported too: the landscape is drawn from it.
"""
import collections
import ctypes
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import callwrites as cw  # noqa: E402

REG_D = [cw.REG_D0 + i for i in range(8)]
REG_A = [cw.REG_A0 + i for i in range(8)]
RENDER = 0x65174
BUCKETS = 0x64d94       # the depth lists' write pointers and ends ($29594)
SHIP = 0x1060           # the ship's position and velocity
CAM = 0x107e
MATRIX = 0x1084
P_ITER, O_ITER = 0x60a42, 0x624de
P_TAILS = {0x60a52: 'dot', 0x60ac2: 'dot+ground', 0x60b66: 'shard'}
O_TAIL, L_POINTS, S_STORE = 0x62508, 0x63484, 0x66a50
P_STORES = (0x60aa4, 0x60b12, 0x60b48)
SHARD_STORE = 0x60bbc
O_STORE, L_STORE = 0x625ac, 0x634dc
PARTICLE = ('dot', 'dot+ground', 'shard')
WRITERS = PARTICLE + ('object', 'lightning', 'ship')
SPINS = {0x109c: 'spin $109c', 0x10ae: 'spin $10ae', 0x10c0: 'spin $10c0', 0x10d2: 'identity',
         0x1084: 'own ($1084)'}
CODECB = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint32, ctypes.c_void_p)
P_FIELDS = ('x', 'y', 'z', 'vx', 'vy', 'vz', 'life', 'handler', 'handler')
O_FIELDS = ('x', 'y', 'z', 'w3', 'w4', 'w5', 'w6', 'w7', 'handler', 'handler')


def s16(v):
    v &= 0xffff
    return v - 0x10000 if v & 0x8000 else v


def words(b):
    return [int.from_bytes(b[i:i + 2], 'big') for i in range(0, len(b), 2)]


def band(n):
    """A histogram bin: 0, 1, 2, 3-4, 5-8, ... 2^k+1 to 2^(k+1)."""
    if n <= 2:
        return n
    k = (n - 1).bit_length()
    return 1 << k


class Recorder:
    def __init__(self, m):
        self.m = m
        self.cbs = []
        hook = m.uc.uc_hook_add
        hook.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_int,
                         ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64]
        table = [(P_ITER, self.p_iter), (O_ITER, self.o_iter), (O_TAIL, self.o_tail),
                 (L_POINTS, self.l_points), (S_STORE, self.s_store)]
        table += [(a, self.p_tail) for a in P_TAILS]
        table += [(a, self.store) for a in P_STORES + (SHARD_STORE, O_STORE, L_STORE)]
        for addr, fn in table:
            cb = CODECB(lambda uc, addr, size, user, fn=fn: fn(addr))
            hh = ctypes.c_size_t()
            assert hook(m.h, ctypes.byref(hh), 4, ctypes.cast(cb, ctypes.c_void_p), None,
                        addr, addr) == 0
            self.cbs.append(cb)
        self.new_tick()

    def a(self, i):
        return self.m.reg(REG_A[i])

    def new_tick(self):
        self.src, self.cur_p, self.cur_o, self.last = [], None, None, None

    def add(self, s):
        s['entries'] = []
        self.src.append(s)
        self.last = s

    def p_iter(self, pc):
        a6 = self.a(6)
        self.cur_p = (a6 - 14, self.m.read(a6 - 14, 18))

    def o_iter(self, pc):
        a6 = self.a(6)
        self.cur_o = (a6, self.m.read(a6, 20))

    def p_tail(self, pc):
        slot = self.a(6) - 18
        self.add({'kind': P_TAILS[pc], 'slot': slot, 'rec': self.m.read(slot, 18),
                  'pre': self.cur_p, 'model': self.a(5), 'mptr': self.a(4),
                  'matrix': self.m.read(self.a(4), 18) if P_TAILS[pc] == 'shard' else None})

    def o_tail(self, pc):
        slot = self.a(6) - 20
        self.add({'kind': 'object', 'slot': slot, 'rec': self.m.read(slot, 20),
                  'pre': self.cur_o, 'model': self.a(5), 'mptr': self.a(4), 'matrix': self.m.read(self.a(4), 18)})

    def l_points(self, pc):
        slot = self.a(6) - 20
        self.add({'kind': 'lightning', 'slot': slot, 'rec': self.m.read(slot, 20),
                  'pre': self.cur_o, 'model': None, 'matrix': None})

    def s_store(self, pc):
        self.add({'kind': 'ship', 'slot': SHIP, 'rec': None, 'pre': None, 'model': None,
                  'mptr': MATRIX,
                  'matrix': self.m.read(MATRIX, 18)})
        self.store(pc)

    def store(self, pc):
        if pc in P_STORES:
            entry, bucket, n = self.a(4), self.m.reg(REG_D[6]) & 0xffff, 8
        elif pc == L_STORE:
            entry, bucket, n = self.a(1), self.m.reg(REG_D[6]) & 0xffff, 16
        else:
            entry, bucket, n = self.a(1), (self.a(0) - BUCKETS) & 0xffff, 32
        self.last['entries'].append((bucket, entry, n))

    def collect(self):
        """The entries as the renderer finds them."""
        for s in self.src:
            s['entries'] = [(b, self.m.read(e, n)) for b, e, n in s['entries']]
        return self.src


class Stats:
    def __init__(self):
        self.c = collections.defaultdict(collections.Counter)
        self.move = collections.defaultdict(collections.Counter)
        self.mat = collections.defaultdict(collections.Counter)
        self.cam = collections.Counter()
        self.handlers = collections.Counter()

    def pair(self, prev, cur, cam0, cam1, ends):
        self.cam[band(max(abs(s16(a - b)) for a, b in zip(cam0, cam1)))] += 1
        before = {(s['kind'] in PARTICLE, s['slot']): s for s in prev if s['kind'] != 'lightning'}
        light = {s['slot']: s for s in prev if s['kind'] == 'lightning'}
        where = {g: collections.defaultdict(list) for g in (True, False)}
        for g, table in ends.items():
            for slot, rec in table.items():
                where[g][rec].append(slot)
        used = set()
        for s in cur:
            k = s['kind']
            if k == 'object':
                self.handlers[int.from_bytes(s['rec'][16:20], 'big')] += 1
            c = self.c[k]
            c['entries'] += len(s['entries'])
            if k == 'ship':
                p = before.get((False, SHIP))
            elif k == 'lightning':
                p = light.get(s['slot'])
            else:
                g, (slot, rec) = k in PARTICLE, s['pre']
                # the slot this record had at the end of the last tick: its own, or the last
                # one, which a removal copies into the freed slot
                had = where[g].get(rec, [])
                if not had:
                    c['unpaired: spawned during the dispatcher'] += 1
                    continue
                old = slot if slot in had else had[0]
                p = before.get((g, old))
                if p is None:
                    c['unpaired: spawned after the dispatcher'] += 1
                    continue
                if p['rec'] != rec:
                    fields = P_FIELDS if g else O_FIELDS
                    diff = sorted({fields[i] for i, (x, y) in
                                   enumerate(zip(words(p['rec']), words(rec))) if x != y})
                    c['unpaired: changed after its tail (' + ' '.join(diff) + ')'] += 1
                    continue
                if old != slot:
                    c['paired, moved to another slot'] += 1
            if p is None:
                c['unpaired: new'] += 1
                continue
            used.add(id(p))
            c['pairs'] += 1
            if p['kind'] != k:
                c[f"writer changed ({p['kind']} -> {k})"] += 1
                continue
            a, b = p['entries'], s['entries']
            if len(a) != len(b):
                c['shown on one tick only'] += 1
                continue
            if not a:
                c['culled on both'] += 1
                continue
            c['shown on both'] += 1
            for (ba, ea), (bb, eb) in zip(a, b):
                if ea[:4] != eb[:4]:
                    c['plotter changed'] += 1
                if ba != bb:
                    c['bucket changed'] += 1
                wa, wb = words(ea), words(eb)
                if len(ea) == 8:
                    d = max(abs(s16(x - y)) for x, y in zip(wa[2:], wb[2:]))
                elif len(ea) == 16:
                    d = max(abs(s16(x - y)) for x, y in zip(wa[2:], wb[2:]))
                else:
                    if ea[4:8] != eb[4:8]:
                        c['model changed'] += 1
                    d = max(abs(s16(x - y)) for x, y in zip(wa[13:], wb[13:]))
                    md = max(abs(s16(x - y)) for x, y in zip(wa[4:13], wb[4:13]))
                    src = 'ship' if k == 'ship' else SPINS.get(p['mptr'], 'own')
                    if k != 'ship' and src != SPINS.get(s['mptr'], 'own'):
                        src += ' (source changed)'
                    self.mat[(k, src)][band(md)] += 1
                self.move[k][band(d)] += 1
        for s in prev:
            if id(s) not in used:
                self.c[s['kind']]['tick N-1 source with none on tick N'] += 1

    def report(self, ticks):
        print(f'{ticks} ticks; the camera step a tick (largest component, units): '
              + hist(self.cam))
        for k in WRITERS:
            c = self.c.get(k)
            if not c:
                continue
            n = c['pairs'] + sum(v for x, v in c.items() if x.startswith('unpaired'))
            print(f"{k}: {n} sources, {c['pairs']} paired ({100 * c['pairs'] / max(n, 1):.1f}%), "
                  f"{c['entries']} entries")
            for x, v in sorted(c.items(), key=lambda kv: -kv[1]):
                if x not in ('pairs', 'entries'):
                    print(f'    {x}: {v}')
            if self.move.get(k):
                unit = 'pixels' if k in ('dot', 'dot+ground') else 'units'
                print(f'    position step ({unit}): ' + hist(self.move[k]))
            if k == 'object':
                print('    tails by handler (Disk.1): ' + ' '.join(
                    f'${h - 0x3b800:05x}x{n}' for h, n in sorted(self.handlers.items())))
            for (kk, src), h in sorted(self.mat.items()):
                if kk == k:
                    print(f'    matrix word step, {src}: ' + hist(h))


def hist(c):
    return ' '.join(f'{lo}x{n}' if lo <= 2 else f'{lo // 2 + 1}-{lo}x{n}' for lo, n in sorted(c.items()))


def tables(m):
    """The particle and object records at the end of a tick, by slot."""
    out = {}
    for g, base, size, count in ((True, 0xa2a6, 18, 0xc9ec), (False, 0xbd04, 20, 0xc9ee)):
        n = int.from_bytes(m.read(count, 2), 'big')
        raw = m.read(base, n * size)
        out[g] = {base + i * size: raw[i * size:(i + 1) * size] for i in range(n)}
    return out


def run(dump, ticks):
    m = cw.Machine(Path(dump).read_bytes()[:cw.CHIP])
    r = Recorder(m)
    st = Stats()
    prev = cam0 = ends = None
    done = 0
    for _ in range(ticks):
        r.new_tick()
        c = int.from_bytes(m.read(0xc9f4, 2), 'big')
        m.write(0xc9f4, ((c + 1) & 0xffff).to_bytes(2, 'big'))
        try:
            for pc in cw.CALLS:
                if pc == RENDER:
                    cur = r.collect()
                    cam1 = tuple(words(m.read(CAM, 6)))
                m.call(pc)
        except RuntimeError as e:
            print(f'stopped at tick {c + 1}: {e}')
            break
        if prev is not None:
            st.pair(prev, cur, cam0, cam1, ends)
            done += 1
        prev, cam0, ends = cur, cam1, tables(m)
    st.report(done)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 400)
