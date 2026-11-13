"""English to German CD32 address map, derived from the two pinned executables.

wing.german is the same program built with German text: its code is the English
code with shifted addresses and its data hunk (and so its A4-relative
variables) is laid out with longer strings. Aligning the two code hunks
instruction by instruction (address operands masked: branch and PC-relative
targets, A4 displacements and relocated longs; every other number must be
equal) pairs every matched English
instruction with its German twin. From the pairs:

- code(e): the German code offset of English hunk-0 offset e, at or inside a
  matched instruction of equal size;
- a4(n): the German A4 offset of English A4 offset n, as observed in matched
  instructions' A4 displacements, or between two observed neighbours with the
  same shift;
- hunk3(e): the same for the small second code hunk.

Text inside the code hunk can desynchronise the disassembly just before a
routine, so routine entries the alignment misses are also taken from matched
calls and branches: an absolute (relocated) or PC-relative target in a matched
instruction pairs with its twin's target. A few bytes just before a matched
run also map with it when they are byte-identical in both files.

Every lookup refuses what it cannot establish, so a build fails rather than
guess. The map holds offsets only; it is cached under tmp/ keyed by both input
digests.
"""
import bisect
import difflib
import hashlib
import json
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGLISH = ('tmp/game/WingCommanderCD32/data/wing.english',
           '093505483aed4c9dbd1b97484c3336e92fdb156be9c15a67ed0199bd4dade657')
GERMAN = ('tmp/game/WingCommanderCD32/data/wing.german',
          '2047da69f2c83803675921afd86204747609a5c59dd3e7f67d954d785677dabe')
VERSION = 3
A4_BASE = 0x7ffe
# Observed A4 pairs that disagree with both neighbours come from instructions
# the alignment paired by shape only; these are excluded unless listed here.
A4_CONFIRMED = {}


def load(path):
    b = path.read_bytes(); o = 4
    while struct.unpack_from('>I', b, o)[0]:
        o += 4
    o += 4; _, first, last = struct.unpack_from('>III', b, o); o += 12+4*(last-first+1)
    hunks = []; rel = []
    while o < len(b):
        t = struct.unpack_from('>I', b, o)[0] & 0x3fffffff; o += 4
        if t in (0x3e9, 0x3ea):
            n = struct.unpack_from('>I', b, o)[0]*4
            hunks.append(bytes(b[o+4:o+4+n])); rel.append({}); o += 4+n
        elif t == 0x3eb:
            o += 4; hunks.append(b''); rel.append({})
        elif t == 0x3ec:
            while True:
                c = struct.unpack_from('>I', b, o)[0]; o += 4
                if not c:
                    break
                h = struct.unpack_from('>I', b, o)[0]; o += 4
                for i in range(c):
                    rel[-1][struct.unpack_from('>I', b, o+4*i)[0]] = h
                o += 4*c
        elif t != 0x3f2:
            raise ValueError('unexpected hunk type %x' % t)
    return hunks, rel


A4_OPERAND = re.compile(r'(-?\$?[0-9a-f]+)\(a4\)|\((-?\$?[0-9a-f]+), a4')


def number(text):
    sign = -1 if text.startswith('-') else 1
    text = text.lstrip('-')
    value = int(text[1:], 16) if text.startswith('$') else int(text)
    value *= sign
    return value-0x10000 if value >= 0x8000 else value


def key(x):
    """An instruction with its address operands masked."""
    ops = x[3]
    if x[2].split('.')[0] in ('bra', 'bsr', 'jsr', 'jmp') or re.match(r'^(b..|db..)(\.[bwls])?$', x[2]):
        ops = re.sub(r'\$[0-9a-f]+$', 'T', ops)
    ops = re.sub(r'-?\$?[0-9a-f]+(?=\((a4|pc)[),])', 'A', ops)
    ops = re.sub(r'\((-?\$?[0-9a-f]+), (a4|pc)', '(A, \\2', ops)
    ops = re.sub(r'\$[0-9a-f]+\.l', 'L', ops)
    return x[2]+' '+ops


def shape(code, at, count=4):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_020)
    out = []
    for i in md.disasm(code[at:at+64], at):
        out.append(key((i.address, i.size, i.mnemonic, i.op_str)))
        if len(out) == count:
            break
    return out


def align(e_code, g_code, e_rel, g_rel):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_020)
    md.skipdata = True

    def stream(code):
        return [(i.address, i.size, i.mnemonic, i.op_str) for i in md.disasm(code, 0)]
    e = stream(e_code); g = stream(g_code)
    branch = re.compile(r'^\$([0-9a-f]+)$')

    def targets(x, code, rel):
        out = [struct.unpack_from('>I', code, a)[0] for a in range(x[0], x[0]+x[1]) if rel.get(a) == 0]
        m = branch.match(x[3])
        if m and x[2].split('.')[0] in ('bsr', 'bra', 'jsr', 'jmp'):
            out.append(int(m[1], 16))
        return out

    blocks = difflib.SequenceMatcher(None, [key(x) for x in e], [key(x) for x in g],
                                     autojunk=False).get_matching_blocks()
    pairs = []; a4 = defaultdict(Counter); calls = defaultdict(Counter)
    for a, b, n in blocks:
        for k in range(n):
            x, y = e[a+k], g[b+k]
            pairs.append((x[0], y[0], x[1], y[1]))
            et, gt = targets(x, e_code, e_rel), targets(y, g_code, g_rel)
            if len(et) == len(gt):
                for p, q in zip(et, gt):
                    calls[p][q] += 1
            ex = [number(m[0] or m[1]) for m in A4_OPERAND.findall(x[3])]
            gx = [number(m[0] or m[1]) for m in A4_OPERAND.findall(y[3])]
            if len(ex) == len(gx):
                for p, q in zip(ex, gx):
                    a4[p][q] += 1
    return pairs, a4, calls


def build():
    paths = []
    for rel, sha in (ENGLISH, GERMAN):
        data = (ROOT/rel).read_bytes()
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError('changed CD32 executable: '+rel)
        paths.append(ROOT/rel)
    cache = ROOT/'tmp/german-map.json'
    tag = f'{VERSION}:{ENGLISH[1]}:{GERMAN[1]}'
    if cache.exists():
        stored = json.loads(cache.read_text())
        if stored.get('tag') == tag:
            return stored
    (eh, er), (gh, gr) = load(paths[0]), load(paths[1])
    result = dict(tag=tag)
    a4 = defaultdict(Counter)
    for hunk in (0, 3):
        pairs, observed, calls = align(eh[hunk], gh[hunk], er[hunk], gr[hunk])
        result[f'hunk{hunk}'] = pairs
        result[f'calls{hunk}'] = {str(k): dict(v) for k, v in calls.items()}
        for k, v in observed.items():
            a4[k].update(v)
    result['a4'] = {str(k): dict(v) for k, v in a4.items()}
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(json.dumps(result))
    return result


class Map:
    def __init__(self):
        data = build()
        self.english, erel = load(ROOT/ENGLISH[0])
        self.german, grel = load(ROOT/GERMAN[0])
        self.relocs = (erel, grel)
        self.hunks = {}; self.calls = {}
        for hunk in (0, 3):
            pairs = sorted(data[f'hunk{hunk}'])
            self.hunks[hunk] = ([p[0] for p in pairs], pairs)
            # Only targets every matched caller agrees on.
            self.calls[hunk] = {int(k): int(next(iter(v))) for k, v in data[f'calls{hunk}'].items()
                                if len(v) == 1}
        votes = {int(k): Counter({int(g): n for g, n in v.items()}) for k, v in data['a4'].items()}
        keys = sorted(votes)
        delta = {k: votes[k].most_common(1)[0][0]-k for k in keys}
        self.a4_pairs = {}
        for i, k in enumerate(keys):
            if len(votes[k]) > 1 and k not in A4_CONFIRMED:
                continue
            neighbours = [delta[keys[j]] for j in (i-1, i+1) if 0 <= j < len(keys)]
            if delta[k] not in neighbours and k not in A4_CONFIRMED:
                continue
            self.a4_pairs[k] = k+delta[k]
        self.a4_pairs.update(A4_CONFIRMED)
        self.a4_keys = sorted(self.a4_pairs)

    def _before_run(self, hunk, e):
        starts, pairs = self.hunks[hunk]
        j = bisect.bisect_right(starts, e)
        if j >= len(starts) or starts[j]-e > 16:
            return None
        g = pairs[j][1]-(starts[j]-e)
        n = starts[j]-e
        if self.english[hunk][e:e+n] != self.german[hunk][g:g+n]:
            return None
        if any(a in self.relocs[0][hunk] for a in range(e-3, e+n)) or \
                any(a in self.relocs[1][hunk] for a in range(g-3, g+n)):
            return None
        return g

    def _call(self, hunk, e):
        g = self.calls[hunk][e]
        if shape(self.english[hunk], e) != shape(self.german[hunk], g):
            raise ValueError(f'hunk {hunk} offset {e:#x}: call target {g:#x} differs in shape')
        return g

    def _code(self, hunk, e, strict=False):
        starts, pairs = self.hunks[hunk]
        before = self._before_run(hunk, e)
        if before is not None and (bisect.bisect_right(starts, e) == 0 or
                                   not starts[bisect.bisect_right(starts, e)-1] <= e <
                                   starts[bisect.bisect_right(starts, e)-1]+pairs[bisect.bisect_right(starts, e)-1][2]):
            return before
        i = bisect.bisect_right(starts, e)-1
        if i < 0 and not strict and e in self.calls[hunk]:
            return self._call(hunk, e)
        if i < 0:
            raise ValueError(f'hunk {hunk} offset {e:#x}: before the first matched instruction')
        start, g, esize, gsize = pairs[i]
        if not start <= e < start+esize:
            if not strict and e in self.calls[hunk]:
                return self._call(hunk, e)
            raise ValueError(f'hunk {hunk} offset {e:#x}: not in a matched instruction')
        if (strict or e != start) and esize != gsize:
            raise ValueError(f'hunk {hunk} offset {e:#x}: inside a resized instruction')
        return g+(e-start)

    def code(self, e):
        return self._code(0, e)

    def hunk3(self, e):
        return self._code(3, e)

    def word(self, e, hunk=0):
        g = self._code(hunk, e, strict=True)
        return struct.unpack_from('>H', self.german[hunk], g)[0]

    def a4(self, n):
        if n in self.a4_pairs:
            return self.a4_pairs[n]
        i = bisect.bisect_left(self.a4_keys, n)
        if 0 < i < len(self.a4_keys):
            lo, hi = self.a4_keys[i-1], self.a4_keys[i]
            if self.a4_pairs[lo]-lo == self.a4_pairs[hi]-hi:
                return n+self.a4_pairs[lo]-lo
        raise ValueError(f'A4 offset {n}: no observed shift')

    def span(self, n, length):
        """An A4 block copied whole must keep one shift across its length."""
        shift = self.a4(n)-n
        inside = [k for k in self.a4_keys if n <= k < n+length]
        if self.a4(n+length-2)-(n+length-2) != shift or \
                any(self.a4_pairs[k]-k != shift for k in inside):
            raise ValueError(f'A4 block {n}+{length}: German shift is not uniform')
        return shift

    def data(self, e):
        return self.a4(e-A4_BASE)+A4_BASE


_map = None


def get():
    global _map
    if _map is None:
        _map = Map()
    return _map


# Language symbols in CD32 sources: E_<hex> code (hunk 0) and E3_<hex> hunk-3
# offsets, D_<hex> data-hunk offsets, A_<dec>/A_m<dec> and AX_<hex>/AX_m<hex>
# A4 offsets (decimal or hex as written), W_<hex>/W3_<hex> the native word at
# a code offset. English values are the names' own numbers (and the English
# words), so English builds are unchanged; english() restores the literals for
# the OCS adapters, which map the same sources to OCS addresses.
SYMBOL = re.compile(r'\b(E|E3|D|W|W3)_([0-9a-f]+)\b|\b(A|AX)_(m?)([0-9a-f]+)\b')


def _english_words():
    hunks, _ = load(ROOT/ENGLISH[0])
    return hunks


def english(text):
    words = []

    def literal(match):
        if match[1] is None:
            sign = '-' if match[4] else ''
            return f'{sign}{match[5]}' if match[3] == 'A' else f'{sign}${match[5]}'
        if match[1] in ('W', 'W3'):
            if not words:
                words.append(_english_words())
            hunk = 3 if match[1] == 'W3' else 0
            return '$%x' % struct.unpack_from('>H', words[0][hunk], int(match[2], 16))[0]
        return '$'+match[2]
    return SYMBOL.sub(literal, text)


def check_blocks(text):
    """Scene range tables (A4 start, word count-1) and the funeral state."""
    m = get()
    blocks = set()
    for line in text.splitlines():
        line = line.split(';')[0]
        if 'dc.w' in line and 'AX_' in line:
            items = [x.strip() for x in line.split('dc.w', 1)[1].split(',')]
            for a, b in zip(items, items[1:]):
                if a.startswith('AX_') and b.isdigit():
                    blocks.add((int(a[3:], 16), 2*(int(b)+1)))
    state = re.search(r'^FUNERAL_STATE equ A_(\d+)$', text, re.M)
    size = re.search(r'^FUNERAL_BYTES equ (\d+)$', text, re.M)
    if state and size:
        blocks.add((int(state[1]), int(size[1])))
    for start, length in sorted(blocks):
        m.span(start, length)
    return len(blocks)


def equates(text, german=False):
    m = get() if german else None
    words = None
    values = {}
    for match in SYMBOL.finditer(text):
        name = match[0]
        if name in values:
            continue
        if match[1] is None:
            n = int(match[5], 10 if match[3] == 'A' else 16)
            n = -n if match[4] else n
            values[name] = m.a4(n) if german else n
            continue
        kind, off = match[1], int(match[2], 16)
        if kind == 'E':
            values[name] = m.code(off) if german else off
        elif kind == 'E3':
            values[name] = m.hunk3(off) if german else off
        elif kind == 'D':
            values[name] = m.data(off) if german else off
        else:
            hunk = 3 if kind == 'W3' else 0
            if german:
                values[name] = m.word(off, hunk)
            else:
                words = words or _english_words()
                values[name] = struct.unpack_from('>H', words[hunk], off)[0]
    return ''.join(f'{k} equ {v}\n' for k, v in sorted(values.items()))


class Symbols:
    """Generator helpers: language symbols for CD32, literals for OCS."""

    def __init__(self, variant):
        self.cd32 = variant == 'cd32'

    def code(self, off, hunk=0):
        if not self.cd32:
            return f'${off:x}'
        return f'E3_{off:x}' if hunk == 3 else f'E_{off:x}'

    def word(self, code, off, hunk=0):
        if not self.cd32:
            return '$%x' % int.from_bytes(code[off:off+2], 'big')
        return f'W3_{off:x}' if hunk == 3 else f'W_{off:x}'

    def a4(self, n):
        if not self.cd32:
            return str(n)
        return f'A_m{-n}' if n < 0 else f'A_{n}'

    def copy(self, code, start, end, hunk=0):
        """A native span: German builds take the German instruction words."""
        if not self.cd32:
            return ' dc.b '+','.join(str(x) for x in code[start:end])
        assert start % 2 == 0 and end % 2 == 0
        return ' dc.w '+','.join(self.word(code, o, hunk) for o in range(start, end, 2))
