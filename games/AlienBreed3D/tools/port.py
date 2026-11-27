#!/usr/bin/env python3
"""Game offsets of the $c4dc version (tmp/exe) mapped to the CD32 one ($fd78, tmp/exe-cd32).

    python3 tools/port.py OFF...      (hex) each offset's CD32 offset and how it was found
    python3 tools/port.py check       every site Enhanced resolution uses (src/): mapped, and
                                      the bytes it patches the same in both (relocated longs
                                      aside); prints each with its distance between the two;
                                      and src/cd32.s and cd32segs.s current
    python3 tools/port.py gen         write src/cd32.s (_pl_v2's CUSTOM5 block: _pl_v3's,
                                      mapped) and src/cd32segs.s (port.s's segments)

Both images are `tools/exe.py`'s (hunks end to end, relocated to 0). The CD32 version is the
same game with its code at other offsets (resolution plan step 9), so:

- code: the bytes around OFF, the relocated longs masked out in both, are found once in the
  CD32 image (a window from 32 bytes growing to 512 until it is unique), or as many times
  as in the $c4dc image (repeated code: the n-th maps to the n-th); else a neighbour within
  32 bytes that maps, with the bytes between the same in both;
- data (no unique context: zeros, tables; a window needs 12 unmasked bytes of 4 different
  values): the code that references it. Every relocated long
  in the $c4dc image that points at OFF, or a little below (a table's base with OFF inside),
  is mapped as code; its CD32 long, plus the same distance, is OFF's. All references must
  agree. References to OFF itself win over a different context (data in padding whose
  length differs) when there are two or more;
- the chip hunks are the same sizes in both, at a fixed distance.

`port(off)` raises PortError when none of these gives one answer.
"""
import bisect
import os
import struct
import sys

GAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(GAME, 'tools'))
from exe import flatten  # noqa: E402


class PortError(Exception):
    pass


class Image:
    def __init__(self, path):
        self.hunks, self.data, self.relocs = flatten(open(path, 'rb').read())
        self.mask = bytearray(len(self.data))
        for r in self.relocs:
            self.mask[r:r + 4] = b'\1\1\1\1'
        self.by_target = {}
        for r in self.relocs:
            self.by_target.setdefault(self.long(r), []).append(r)
        self.targets = sorted(self.by_target)

    def long(self, a):
        return struct.unpack('>I', self.data[a:a + 4])[0]

    def hunk(self, a):
        for i, (o, s, _) in enumerate(self.hunks):
            if o <= a < o + s:
                return i
        raise PortError(f'${a:x} is outside the image')


_images = {}


def images():
    if not _images:
        _images['a'] = Image(os.path.join(GAME, 'tmp/exe/abd'))
        _images['b'] = Image(os.path.join(GAME, 'tmp/exe-cd32/abd'))
    return _images['a'], _images['b']


def _matches(a, b, lo, hi):
    """Offsets in b where a[lo:hi] occurs, relocated longs masked (in both)."""
    win, m = a.data[lo:hi], a.mask[lo:hi]
    # the longest unmasked run is the search key
    best, i = (0, 0), 0
    while i < len(win):
        if m[i]:
            i += 1
            continue
        j = i
        while j < len(win) and not m[j]:
            j += 1
        if j - i > best[1] - best[0]:
            best = (i, j)
        i = j
    k0, k1 = best
    # zeros or one repeated word find a run of padding, not the place: the key at least 4
    # bytes, the window's unmasked bytes at least 12 with 4 different values
    free = bytes(win[i] for i in range(len(win)) if not m[i])
    if k1 - k0 < 4 or len(free) < 12 or len(set(free)) < 4:
        return None
    key, out, p = win[k0:k1], [], b.data.find(win[k0:k1])
    while p >= 0:
        s = p - k0
        if s >= 0 and s + len(win) <= len(b.data) and b.mask[s:s + len(win)] == m and \
                all(m[i] or b.data[s + i] == win[i] for i in range(len(win))):
            out.append(s)
        p = b.data.find(key, p + 1)
    return out


def _windows(off, a):
    for half in (16, 32, 64, 128, 256):
        # windows around, ending at and starting at off: a site at a routine's end or start
        for lo, hi in ((off - half, off + half), (off - 2 * half + 4, off + 4),
                       (off, off + 2 * half)):
            yield max(lo, 0), min(hi, len(a.data))


def _context(off, a, b):
    """A window found once in b; or as often in b as in a (repeated code), taken in order."""
    ranked = None
    for lo, hi in _windows(off, a):
        got = _matches(a, b, lo, hi)
        if not got:
            continue
        if len(got) == 1:
            return got[0] + off - lo
        if ranked is None:
            mine = _matches(a, a, lo, hi)
            if mine and len(mine) == len(got) and lo in mine:
                ranked = got[mine.index(lo)] + off - lo
    return ranked


def port_code(off, a=None, b=None):
    if a is None:
        a, b = images()
    x = _context(off, a, b)
    if x is not None:
        return x
    # a neighbour within 32 bytes that maps, the bytes between the same (code around the
    # site changed further on, as a call one version has and the other not)
    for k in range(2, 34, 2):
        for anchor in (off - k, off + k):
            y = _context(anchor, a, b)
            if y is None:
                continue
            lo, hi = min(anchor, off), max(anchor, off) + 4
            d = y - anchor
            if all((a.mask[i] and b.mask[i + d]) or a.data[i] == b.data[i + d]
                   for i in range(lo, hi)):
                return off + d
    raise PortError(f'${off:x}: no unique code context')


def port_data(off, a=None, b=None, exact=False):
    """By the references to off itself, else (exact False) to the nearest target below it
    (within 64 KB)."""
    if a is None:
        a, b = images()
    i = bisect.bisect_right(a.targets, off)
    for t in reversed(a.targets[max(0, i - 8):i]):
        if off - t > 0x10000 or (exact and t != off):
            break
        answers = set()
        for r in a.by_target[t]:
            try:
                q = port_code(r, a, b)
            except PortError:
                continue
            answers.add(b.long(q) + off - t)
        if len(answers) == 1:
            return answers.pop()
        if len(answers) > 1:
            raise PortError(f'${off:x}: references disagree ' +
                            ' '.join(f'${x:x}' for x in sorted(answers)))
    raise PortError(f'${off:x}: no mapped reference')


def port(off):
    """(CD32 offset, how)."""
    a, b = images()
    h = a.hunk(off)
    if h > 0:
        x = off - a.hunks[h][0] + b.hunks[h][0]
        return x, 'chip hunk'
    try:
        code = port_code(off, a, b)
    except PortError as e:
        code, code_err = None, e
    try:
        data = port_data(off, a, b, exact=True)
    except PortError:
        data = None
    if data is not None:
        if code is not None and code != data:
            # padding around off is longer or shorter in one image: what the code uses wins,
            # given more than one reference
            if len(a.by_target[off]) < 2:
                raise PortError(f'${off:x}: context ${code:x}, one reference ${data:x}')
            return data, f'references (context ${code:x})'
        return data, 'references' if code is None else 'code and references'
    if code is not None:
        return code, 'code'
    try:
        return port_data(off, a, b), 'a table\'s references'
    except PortError as e:
        raise PortError(f'{code_err}; {e}')


# the sites in src/ that hold $c4dc offsets: PL_ lines of the CUSTOM5 block (from PL_IFC5 to
# its PL_ENDIF, with every IFD inside), stride.s, sites.s, port.s's G_ entries (GOFS) and
# the tables of offsets port.s translates. (kind, offset, bytes compared, where)
PL_LEN = {'PL_W': 2, 'PL_L': 4, 'PL_PS': 6, 'PL_P': 6, 'PL_R': 2}
TABLES = {'_ds_stridetabs': 4, '_t_ptrs': 0, '_t_penptrs': 0, '_t_halve': 2}  # bytes a count
PL_RE = r'(\s+)(PL_\w+)(\s+)\$([0-9a-f]+)(.*)'


def _src(name):
    return open(os.path.join(GAME, 'src', name)).read().split('\n')


def block():
    """The $c4dc CUSTOM5 block's lines, PL_IFC5 to its PL_ENDIF."""
    import re
    lines = _src('AlienBreed3D.s')
    start = next(i for i, l in enumerate(lines) if l.startswith('_pl_v3'))
    first = next(i for i in range(start, len(lines)) if re.match(r'\s+PL_IFC5\b', lines[i]))
    last = next(i for i in range(first, len(lines)) if re.match(r'\s+PL_ENDIF\b', lines[i]))
    return first, lines[first:last + 1]


def sites():
    import re
    out = []

    def pl(line, where):
        m = re.match(PL_RE, line)
        if not m:
            return
        kind, off = m.group(2), int(m.group(4), 16)
        arg = m.group(5).split(';')[0].strip().lstrip(',')
        n = int(arg.replace('$', '0x'), 0) if kind in ('PL_S', 'PL_NOP') else PL_LEN[kind]
        out.append((kind, off, n, where))

    first, lines = block()
    for i, l in enumerate(lines):
        pl(l, f'AlienBreed3D.s:{first + i + 1}')
    for i, l in enumerate(_src('stride.s')):
        pl(l, f'stride.s:{i + 1}')
    for i, l in enumerate(_src('sites.s')):
        m = re.match(r'\s+SITE\s+(\d),\$([0-9a-f]+),', l)
        if m:
            out.append(('SITE', int(m.group(2), 16), int(m.group(1)), f'sites.s:{i + 1}'))
    for i, l in enumerate(_src('port.s')):
        m = re.match(r'\s+GOFS\s+(\w+),\$([0-9a-f]+)', l)
        if m:
            out.append(('G_' + m.group(1), int(m.group(2), 16), 0, f'port.s:{i + 1}'))
    for f in ('display.s', 'hires.s'):
        lines, table = _src(f), None
        for i, l in enumerate(lines):
            m = re.match(r'(_\w+)', l)
            if m:
                table = m.group(1) if m.group(1) in TABLES else None
            m = re.match(r'\s+dc\.l\s+\$([0-9a-f]+)', l)
            if table and m:
                n = 4  # an operand long; a table's rows: their count on the next line
                c = re.match(r'\s+dc\.w\s+(\d+)', lines[i + 1]) if TABLES[table] else None
                if c:
                    n = TABLES[table] * int(c.group(1))
                out.append((table, int(m.group(1), 16), n, f'{f}:{i + 1}'))
    return out


HEADER = """; Generated by tools/port.py from {what}: the $c4dc
; version's game offsets mapped to the CD32 one's ($fd78). Do not edit.
"""


def gen_block():
    """_pl_v2's CUSTOM5 block: _pl_v3's, every offset mapped, stride.s inline."""
    import re
    out = [HEADER.format(what="_pl_v3's CUSTOM5 block (AlienBreed3D.s, stride.s)").rstrip()]

    def line(l):
        m = re.match(PL_RE, l)
        if m:
            x, _ = port(int(m.group(4), 16))
            rest = m.group(5).split(';')[0].rstrip()
            return f'{m.group(1)}{m.group(2)}{m.group(3)}${x:x}{rest}'
        code = l.split(';')[0].rstrip()
        return code or None

    for l in block()[1]:
        if re.match(r'\s+INCLUDE\s+stride\.s', l):
            out += [x for x in map(line, _src('stride.s')) if x]
        elif (x := line(l)):
            out.append(x)
    return '\n'.join(out) + '\n'


def gen_segs():
    """(start, distance) pairs: at each site whose distance differs from the one below it."""
    pairs = sorted({(off, port(off)[0] - off) for _, off, _, _ in sites()})
    segs, last = [], 0
    for off, d in pairs:
        if d != last:
            segs.append((off, d))
            last = d
    for off, d in pairs:  # each site through the segments: its own mapping
        got = 0
        for s0, d0 in segs:
            if s0 <= off:
                got = d0
        if got != d:
            raise PortError(f'${off:x}: two mappings, ${off + d:x} and ${off + got:x}')
    out = [HEADER.format(what='the sites of tools/port.py check').rstrip()]
    out += [f'\tdc.l\t${a:x},{d}' for a, d in segs]
    out.append('\tdc.l\t$ffffffff')
    return '\n'.join(out) + '\n'


GENERATED = {'cd32.s': gen_block, 'cd32segs.s': gen_segs}


def check():
    a, b = images()
    bad = 0
    for kind, off, n, where in sites():
        try:
            x, how = port(off)
        except PortError as e:
            print(f'{where:22} {kind:6} ${off:05x}  ERROR {e}')
            bad += 1
            continue
        same = all((a.mask[off + i] and b.mask[x + i]) or a.data[off + i] == b.data[x + i]
                   for i in range(n))
        note = '' if same else '  BYTES DIFFER'
        bad += not same
        print(f'{where:22} {kind:6} ${off:05x} ${x:05x} {x - off:+6d}  {how}{note}')
    for name, fn in GENERATED.items():
        path = os.path.join(GAME, 'src', name)
        if not os.path.exists(path) or open(path).read() != fn():
            print(f'src/{name} is not current: python3 tools/port.py gen')
            bad += 1
    print(f'{bad} problem(s)')
    return 1 if bad else 0


def gen():
    for name, fn in GENERATED.items():
        open(os.path.join(GAME, 'src', name), 'w').write(fn())
        print(f'wrote src/{name}')
    return 0


def main():
    if sys.argv[1:] == ['check']:
        return check()
    if sys.argv[1:] == ['gen']:
        return gen()
    status = 0
    for w in sys.argv[1:]:
        off = int(w.lstrip('$'), 16)
        try:
            x, how = port(off)
            print(f'${off:x} ${x:x} {how}')
        except PortError as e:
            print(f'${off:x} ERROR {e}')
            status = 1
    return status


if __name__ == '__main__':
    sys.exit(main())
