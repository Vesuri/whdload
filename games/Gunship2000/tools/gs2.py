"""gs2.run, the flight program, in a running Session: where it is and its clocks.

Nothing here carries game bytes: signatures come from the installed file
(tmp/game/<the variant's drawer>/data/gs2.run) when needed.

The three versions' gs2.run are builds of one source: VARIANT (default Gunship2000AGA) picks
the file and OFFSETS, the same places in each (found by aligning the code hunks, P8). AGA
hunks: 0 code $19014, 1 data $d578, 2 BSS $e1c4 (any memory), 3 data $2c2c and 4 BSS $18 (chip).
"""
import os
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VARIANT = os.environ.get('VARIANT') or 'Gunship2000AGA'
DRAWERS = dict(Gunship2000ECS='Gunship2000', Gunship2000AGA='Gunship2000AGA',
               Gunship2000CD32='Gunship2000CD32')
GS2 = ROOT / 'tmp/game' / DRAWERS[VARIANT] / 'data/gs2.run'

# Code: present (rotates the screens, once per frame), the frame cap's spin, the VBL wait, the
# renderer routines the slave may replace with a jmp (P5, P7). BSS (hunk 2): the screen just
# drawn, the three screens, the player object, the position table, the clocks (see
# docs/internals.md, "Flight timing").
OFFSETS = {
    'Gunship2000AGA': dict(present=0x129c4, cap_spin=(0x2c6, 0x2cc, 0x2d0), vbl_wait=(0x129aa, 0x129b0),
                           slave_jumps=(0xfab6, 0x13832, 0xfd3c), drawn=0xb8dc,
                           screens=(0xb8e4, 0xb8e8, 0xb8ec), player=0xd348, table=0x127a,
                           ticks=0xc680, seconds=0xc682, fraction=0xc684, dt=0xc67e, accel=0xc696,
                           vbl=0xb8fc),
    'Gunship2000ECS': dict(present=0x125ca, cap_spin=(0x2b0, 0x2b6, 0x2ba), vbl_wait=(0x125b0, 0x125b6),
                           slave_jumps=(0xf9ce, 0x1348a, 0xfc54), drawn=0xb8d4,
                           screens=(0xb8dc, 0xb8e0, 0xb8e4), player=0xd296, table=0x1272,
                           ticks=0xc5ce, seconds=0xc5d0, fraction=0xc5d2, dt=0xc5cc, accel=0xc5e4,
                           vbl=0xb8f4),
    'Gunship2000CD32': dict(present=0x12968, cap_spin=(0x2c4, 0x2ca, 0x2ce), vbl_wait=(0x1294e, 0x12954),
                            slave_jumps=(0xfa70, 0x13806, 0xfcf6), drawn=0xb8dc,
                            screens=(0xb8e4, 0xb8e8, 0xb8ec), player=0xd384, table=0x127a,
                            ticks=0xc6bc, seconds=0xc6be, fraction=0xc6c0, dt=0xc6ba, accel=0xc6d2,
                            vbl=0xb8fc),
}
O = OFFSETS[VARIANT]

CLOCKS = {
    'ticks': (O['ticks'], 2),       # 64 Hz CIA-B ticks since the main loop last took them
    'seconds': (O['seconds'], 2),   # mission clock, whole seconds
    'second_fraction': (O['fraction'], 2),
    'dt': (O['dt'], 2),             # the last frame's time step, 32768 = 15 ticks
    'accel': (O['accel'], 2),       # time acceleration, steps per frame
    'vbl': (O['vbl'], 2),           # +1 every field (the VBL client)
    'tick64': (0x0004, 2),          # 64ths of a second
}

# Code offsets the slave may replace with a jmp to its own routine (the renderer, P5, P7).
SLAVE_JUMPS = O['slave_jumps']


def hunks(path=GS2):
    """[(type, bytes, memflags)] and relocs {hunk: {offset: target}} of a hunk file."""
    d = path.read_bytes()
    u = lambda p: struct.unpack('>I', d[p:p + 4])[0]
    p = 8
    first, last = u(p + 4), u(p + 8)
    p += 12
    flags = [u(p + 4 * i) >> 30 for i in range(last - first + 1)]
    p += 4 * len(flags)
    out, rel, h = [], {}, -1
    while p < len(d):
        t = u(p) & 0x3fffffff
        p += 4
        if t in (0x3e9, 0x3ea):
            h += 1
            n = u(p) * 4
            out.append((t, d[p + 4:p + 4 + n], flags[h]))
            p += 4 + n
        elif t == 0x3eb:
            h += 1
            out.append((t, bytes(u(p) * 4), flags[h]))
            p += 4
        elif t == 0x3ec:
            while True:
                c = u(p)
                p += 4
                if not c:
                    break
                tgt = u(p)
                p += 4
                for i in range(c):
                    rel.setdefault(h, {})[u(p + 4 * i)] = tgt
                p += 4 * c
        elif t == 0x3f2:
            pass
        else:
            raise ValueError(f'unexpected hunk type {t:#x}')
    return out, rel


def library(s, name):
    """Base of an open library, from ExecBase's LibList."""
    eb = s.long(4)
    node = s.long(eb + 0x17a)
    while node and s.long(node):
        np = s.long(node + 10)
        if np and s.read(np, len(name) + 1) == name.encode() + b'\0':
            return node
        node = s.long(node)
    raise LookupError(name)


def memlist(s):
    """Exec's memory headers: [(name, attributes, lower, upper, free)]."""
    eb = s.long(4)
    out, node = [], s.long(eb + 0x142)
    while node and s.long(node):
        b = s.read(node, 32)
        np = int.from_bytes(b[10:14], 'big')
        name = s.read(np, 24).split(b'\0')[0].decode('latin1') if np else ''
        out.append(dict(name=name, attributes=int.from_bytes(b[14:16], 'big'),
                        lower=int.from_bytes(b[20:24], 'big'), upper=int.from_bytes(b[24:28], 'big'),
                        free=int.from_bytes(b[28:32], 'big')))
        node = int.from_bytes(b[:4], 'big')
    return out


def locate(s):
    """Hunk bases of the running gs2.run (searched in Exec's memory), the memory lists, and the
    three screen buffers."""
    hs, rel = hunks()
    code = hs[0][1]
    relocated = set()
    for o in rel.get(0, {}):
        relocated.update(range(o, o + 4))
    # The longest run of unrelocated bytes in the first 4 KB is the signature.
    best, run = (0, 0), 0
    for i in range(0x1000):
        run = 0 if i in relocated else run + 1
        if run > best[1]:
            best = (i - run + 1, run)
    sig_off, n = best[0], min(best[1], 32)
    sig = code[sig_off:sig_off + n]
    mem = memlist(s)
    base0 = None
    for m in mem:
        lo, hi = m['lower'] & ~3, m['upper']
        chunk = 0x40000
        for a in range(lo, hi, chunk):
            b = s.read(a, min(chunk + 64, hi - a))
            i = b.find(sig)
            while i >= 0:
                cand = a + i - sig_off
                if cand >= 0 and verify(s, cand, code, rel[0]):
                    base0 = cand
                    break
                i = b.find(sig, i + 1)
            if base0 is not None:
                break
        if base0 is not None:
            break
    if base0 is None:
        raise LookupError('gs2.run code hunk not found')
    # Each hunk's base by the most common value over its relocations (patches overwrite some).
    image = s.read(base0, len(code))
    votes = {}
    for o, t in rel[0].items():
        v = int.from_bytes(image[o:o + 4], 'big') - int.from_bytes(code[o:o + 4], 'big')
        votes.setdefault(t, {}).setdefault(v & 0xffffffff, 0)
        votes[t][v & 0xffffffff] += 1
    bases = {t: max(c, key=c.get) for t, c in votes.items()}
    bases[0] = base0
    out = dict(hunks={str(h): dict(base=bases[h], size=len(hs[h][1]), type=hs[h][0], memflags=hs[h][2])
                      for h in sorted(bases)},
               memlist=mem)
    h2 = bases[2]
    out['screens'] = [s.long(h2 + o) for o in O['screens']]
    out['slave_jumps'] = slave_jumps(s, base0)
    return out


def slave_jumps(s, base0):
    """{code offset: target} of the slave's `jmp` patches (PL_P) at the renderer's routines, so
    a profile can name the slave's routines."""
    out = {}
    for o in SLAVE_JUMPS:
        b = s.read(base0 + o, 6)
        if b[:2] == b'\x4e\xf9':
            out[f'{o:#x}'] = int.from_bytes(b[2:], 'big')
    return out


def verify(s, base, code, relocs, n=0x400, patched=128):
    """The code hunk at base: the unrelocated bytes of the first n match the file, but for up to
    `patched` (slaves patch the code, CUSTOM2 most of all), and its relocations are applied (the
    file's own image, PRELOADed, matches as well)."""
    b = s.read(base, n)
    relocated = set()
    for o in relocs:
        relocated.update(range(o, o + 4))
    if sum(b[i] != code[i] for i in range(n) if i not in relocated) > patched:
        return False
    first = [o for o in sorted(relocs) if o + 4 <= n]
    return sum(b[o:o + 4] != code[o:o + 4] for o in first) > len(first) // 2


def clocks(s, layout):
    h2 = layout['hunks']['2']['base']
    return {k: int.from_bytes(s.read(h2 + o, n), 'big') for k, (o, n) in CLOCKS.items()}
