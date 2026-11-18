"""gs2.run, the AGA flight program, in a running Session: where it is and its clocks.

Nothing here carries game bytes: signatures come from the installed file
(tmp/game/Gunship2000AGA/data/gs2.run) when needed.

Hunks: 0 code $19014, 1 data $d578, 2 BSS $e1c4 (any memory), 3 data $2c2c and 4 BSS $18 (chip).
"""
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GS2 = ROOT / 'tmp/game/Gunship2000AGA/data/gs2.run'

# BSS (hunk 2) words: see docs/internals.md, "Flight timing".
CLOCKS = {
    'ticks': (0xc680, 2),       # 64 Hz CIA-B ticks since the main loop last took them
    'seconds': (0xc682, 2),     # mission clock, whole seconds
    'second_fraction': (0xc684, 2),
    'dt': (0xc67e, 2),          # the last frame's time step, 32768 = 15 ticks
    'accel': (0xc696, 2),       # time acceleration, steps per frame
    'vbl': (0xb8fc, 2),         # +1 every field (the VBL client)
    'tick64': (0x0004, 2),      # 64ths of a second
}


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
                if cand >= 0 and verify(s, cand, code, relocated):
                    base0 = cand
                    break
                i = b.find(sig, i + 1)
            if base0 is not None:
                break
        if base0 is not None:
            break
    if base0 is None:
        raise LookupError('gs2.run code hunk not found')
    bases = {0: base0}
    for o, t in sorted(rel[0].items()):
        if t not in bases:
            bases[t] = s.long(base0 + o) - int.from_bytes(code[o:o + 4], 'big')
    out = dict(hunks={str(h): dict(base=bases[h], size=len(hs[h][1]), type=hs[h][0], memflags=hs[h][2])
                      for h in sorted(bases)},
               memlist=mem)
    h2 = bases[2]
    out['screens'] = [s.long(h2 + o) for o in (0xb8e4, 0xb8e8, 0xb8ec)]
    return out


def verify(s, base, code, relocated, n=0x400, patched=16):
    """The unrelocated bytes of the first n match the file, but for up to `patched` (slaves
    patch the code)."""
    b = s.read(base, n)
    return sum(b[i] != code[i] for i in range(n) if i not in relocated) <= patched


def clocks(s, layout):
    h2 = layout['hunks']['2']['base']
    return {k: int.from_bytes(s.read(h2 + o, n), 'big') for k, (o, n) in CLOCKS.items()}
