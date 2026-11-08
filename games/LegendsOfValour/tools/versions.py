#!/usr/bin/env python3
"""Map English AMIGA2 offsets to the German and French AMIGA2.

  python3 tools/versions.py summary            per-hunk shifts of each version
  python3 tools/versions.py map hN:OFF...      the offset in each version (h11 also takes a4 displacements as a4:-8134)
  python3 tools/versions.py symbols [--check]  write (or check) src/offsets.s for the hN_OFFSET symbols in src/
  python3 tools/versions.py check              src/offsets.s is current, and every signature compare
                                               (cmp/tst #value,(hN_OFFSET,An)) holds in all three versions

The AMIGA2 files are decrunched on first use into tmp/unpacked/AMIGA2 (English, 0837),
AMIGA2.de (German, 0525) and AMIGA2.fr (French, 1768) from the installed drawers
tmp/game/LegendsOfValour{,De,Fr}/data/AMIGA2 (make unpack). The code hunks are aligned
instruction by instruction (capstone, numbers ignored), so a code offset maps to the matching
instruction. h11 (A4 = h11 + $8000) is mapped through the operands of aligned instructions:
every A4 displacement, absolute relocation and PC-relative target the two versions use at the
same instruction gives a pair, and the majority wins. docs/versions.md.
"""
import bisect, difflib, os, re, struct, sys
from collections import Counter, defaultdict

import capstone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = {'en': 'tmp/unpacked/AMIGA2', 'de': 'tmp/unpacked/AMIGA2.de', 'fr': 'tmp/unpacked/AMIGA2.fr'}
DRAWERS = {'en': 'LegendsOfValour', 'de': 'LegendsOfValourDe', 'fr': 'LegendsOfValourFr'}


def available():
    return all(os.path.exists(os.path.join(ROOT, FILES[n])) or
               os.path.exists(os.path.join(ROOT, 'tmp/game', DRAWERS[n], 'data/AMIGA2')) for n in FILES)


def unpacked(path):
    """FILES[x], decrunched from its installed drawer when it is not there yet."""
    full = os.path.join(ROOT, path)
    if not os.path.exists(full):
        import subprocess
        name = next(n for n, f in FILES.items() if f == path)
        src = os.path.join(ROOT, 'tmp/game', DRAWERS[name], 'data/AMIGA2')
        subprocess.run([sys.executable, os.path.join(ROOT, 'tools/unpack.py'), src, full],
                       check=True, stdout=subprocess.DEVNULL)
    return full
CODE = [h for h in range(17) if h != 11]
NUM = re.compile(r'(?<![\w$])-?(\$[0-9a-f]+|\d+)')


def parse(path):
    b = open(unpacked(path) if path in FILES.values() else os.path.join(ROOT, path), 'rb').read()
    l = lambda o: struct.unpack_from('>I', b, o)[0]
    n = l(8); o = 20 + 4 * n; out = []; i = 0
    allocs = [l(20 + 4 * k) * 4 & 0xffffffff for k in range(n)]
    while o < len(b) and i < n:
        t = l(o) & 0x3fffffff
        if t in (0x3e9, 0x3ea):
            s = l(o + 4) * 4
            out.append({'data': b[o + 8:o + 8 + s], 'rel': {}, 'alloc': allocs[i]}); o += 8 + s
        elif t == 0x3eb:
            out.append({'data': b'', 'rel': {}, 'alloc': allocs[i]}); o += 8
        elif t == 0x3ec:
            o += 4
            while l(o):
                c, th = l(o), l(o + 4)
                for k in range(c):
                    out[-1]['rel'][l(o + 8 + 4 * k)] = th
                o += 8 + 4 * c
            o += 4
        elif t == 0x3f2:
            o += 4; i += 1
        else:
            raise ValueError(hex(t))
    return out


_md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
_md.detail = True


def disasm(data):
    """[(offset, size, key, insn or None)] linearly; undecodable words become data."""
    out, o = [], 0
    while o + 2 <= len(data):
        insn = next(_md.disasm(data[o:o + 10], o, 1), None)
        if insn is None or insn.size == 0 or insn.id == 0:
            out.append((o, 2, 'dc.w ' + data[o:o + 2].hex(), None)); o += 2
        else:
            out.append((o, insn.size, insn.mnemonic + ' ' + NUM.sub('N', insn.op_str), insn))
            o += insn.size
    return out


def operands(insn, hunk, data, rel):
    """Address-like operands: ('a4', h11 offset), ('pc', same-hunk offset), (hunk, offset)."""
    out = []
    for k in range(insn.address, insn.address + insn.size - 3, 2):
        if k in rel:
            out.append((rel[k], struct.unpack_from('>I', data, k)[0], k - insn.address))
    for op in insn.operands:
        if op.type == capstone.m68k.M68K_OP_MEM:
            m = op.mem
            if m.base_reg == capstone.m68k.M68K_REG_A4 and m.index_reg == 0:
                out.append((11, (m.disp + 0x8000) & 0xffff, None))
            elif m.base_reg == capstone.m68k.M68K_REG_PC:
                out.append((hunk, insn.address + 2 + m.disp, None))
        elif op.type == capstone.m68k.M68K_OP_BR_DISP:
            out.append((hunk, insn.address + 2 + op.br_disp.disp, None))
    return out


CACHE = os.path.join(ROOT, 'tmp/versions')


class Version:
    def __init__(self, name):
        import hashlib, pickle
        self.name = name
        en, fo = parse(FILES['en']), parse(FILES[name])
        self.en, self.fo = en, fo
        key = hashlib.sha256(open(__file__, 'rb').read() + open(unpacked(FILES['en']), 'rb').read()
                             + open(unpacked(FILES[name]), 'rb').read()).hexdigest()[:16]
        path = os.path.join(CACHE, '%s-%s.pickle' % (name, key))
        if os.path.exists(path):
            self.code, pairs, self.h11_blocks, self.bss = pickle.load(open(path, 'rb'))
            self.pairs = defaultdict(lambda: defaultdict(Counter))
            for h, d in pairs.items():
                for k, v in d.items():
                    self.pairs[h][k] = v
            return
        self.align()
        os.makedirs(CACHE, exist_ok=True)
        pickle.dump((self.code, {h: dict(d) for h, d in self.pairs.items()}, self.h11_blocks, self.bss),
                    open(path, 'wb'))

    def align(self):
        en, fo = self.en, self.fo
        self.code = {}            # hunk -> sorted [(en_off, fo_off)] of aligned instruction starts
        self.pairs = defaultdict(lambda: defaultdict(Counter))  # hunk -> en_off -> {fo_off}
        for h in CODE:
            a, b = disasm(en[h]['data']), disasm(fo[h]['data'])
            sm = difflib.SequenceMatcher(None, [x[2] for x in a], [x[2] for x in b], autojunk=False)
            m = []
            for i, j, n in sm.get_matching_blocks():
                for k in range(n):
                    x, y = a[i + k], b[j + k]
                    m.append((x[0], y[0]))
                    if x[3] is None:
                        continue
                    ox = operands(x[3], h, en[h]['data'], en[h]['rel'])
                    oy = operands(y[3], h, fo[h]['data'], fo[h]['rel'])
                    if len(ox) == len(oy):
                        for p, q in zip(ox, oy):
                            if p[0] == q[0]:
                                self.pairs[p[0]][p[1]][q[1]] += 1
            self.code[h] = m
        # h11's own pointers into code hunks and itself, aligned with a byte diff of h11.
        a, b = en[11]['data'], fo[11]['data']
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        self.h11_blocks = [blk for blk in sm.get_matching_blocks() if blk[2]]
        for i, j, n in self.h11_blocks:
            for k in range(i, i + n - 3, 2):
                if k in en[11]['rel'] and (j + k - i) in fo[11]['rel']:
                    th = en[11]['rel'][k]
                    self.pairs[th][struct.unpack_from('>I', a, k)[0]][
                        struct.unpack_from('>I', b, j + k - i)[0]] += 1
        self.bss = fo[11]['alloc'] - en[11]['alloc']

    def map(self, h, off):
        """(foreign offset or None, how)."""
        if h in self.code:
            m = self.code[h]
            k = bisect.bisect_right(m, (off, 1 << 30)) - 1
            if k >= 0 and m[k][0] == off:
                return m[k][1], 'insn'
            if k >= 0 and k + 1 < len(m) and m[k + 1][0] - m[k][0] == m[k + 1][1] - m[k][1]:
                return m[k][1] + off - m[k][0], 'inside'
            return None, 'unaligned'
        s = self.pairs[11].get(off)
        if s:
            (best, n), total = s.most_common(1)[0], sum(s.values())
            if n == total:
                return best, 'operand'
            if n * 4 >= total * 3:  # a stray use with another base register
                return best, 'operand %d/%d' % (n, total)
            return None, 'ambiguous %s' % dict(s)
        if off >= len(self.en[11]['data']):
            return off + self.bss, 'bss'
        for i, j, n in self.h11_blocks:
            if i <= off < i + n:
                return j + off - i, 'data'
        return None, 'unmatched'


SYMBOL = re.compile(r'\bh(\d{1,2})_([0-9a-f]{5})\b')
OFFSETS = os.path.join(ROOT, 'src/offsets.s')
# Offsets the alignment cannot decide, decided by hand: (hunk, English) -> (German, French).
OVERRIDES = {}


def used_symbols():
    out = set()
    for name in sorted(os.listdir(os.path.join(ROOT, 'src'))):
        if name.endswith('.s') and name != 'offsets.s':
            for line in open(os.path.join(ROOT, 'src', name)):
                for h, o in SYMBOL.findall(line.split(';')[0]):
                    out.add((int(h), int(o, 16)))
    return sorted(out)


def symbols_text(vs):
    rows, bad = [], []
    for h, o in used_symbols():
        vals = [o]
        for v in vs:
            if (h, o) in OVERRIDES:
                f, how = OVERRIDES[(h, o)][vs.index(v)], 'override'
            else:
                f, how = v.map(h, o)
            if f is None:
                bad.append('h%d_%05x %s: %s' % (h, o, v.name, how))
            vals.append(f)
        if None in vals:
            continue
        rows.append('h%d_%05x\t= LOV_EN*$%05x+LOV_DE*$%05x+LOV_FR*$%05x\n' % (h, o, *vals))
    if bad:
        raise SystemExit('unmapped offsets:\n  ' + '\n  '.join(bad))
    return ('; Generated by tools/versions.py symbols: every hN_OFFSET symbol in src/ is offset OFFSET of\n'
            '; hunk N of the English (0837) AMIGA2 and the matching offset of the German (0525) and\n'
            '; French (1768) one. LegendsOfValourHD.s sets LOV_EN/LOV_DE/LOV_FR from LOV_LANG.\n'
            + ''.join(rows))


SIGNATURE = re.compile(r'^\s+(cmp|cmpi|tst)\.([lwb])\s+(?:#(.+?),)?\(h(\d+)_([0-9a-f]{5}),a\d\)\s*$')


def evaluate(expr, lang):
    """A vasm expression of numbers and hN_OFFSET symbols in one language."""
    def sym(m):
        h, o = int(m.group(1)), int(m.group(2), 16)
        return str(o if lang is None else lang.map(h, o)[0])
    py = SYMBOL.sub(sym, expr)
    py = re.sub(r'\$([0-9a-fA-F]+)', r'0x\1', py)
    if not re.fullmatch(r'[0-9a-fA-Fx+\-*()&|<> ]+', py):
        raise ValueError('cannot evaluate ' + expr)
    return eval(py)


def check_signatures(vs):
    en = parse(FILES['en'])
    count, bad = 0, []
    for name in sorted(os.listdir(os.path.join(ROOT, 'src'))):
        if not name.endswith('.s'):
            continue
        for n, line in enumerate(open(os.path.join(ROOT, 'src', name)), 1):
            m = SIGNATURE.match(line.split(';')[0])
            if not m:
                continue
            size = {'l': 4, 'w': 2, 'b': 1}[m.group(2)]
            h, o = int(m.group(4)), int(m.group(5), 16)
            count += 1
            for lang, hunks in [(None, en)] + [(v, v.fo) for v in vs]:
                at = o if lang is None else lang.map(h, o)[0]
                want = 0 if m.group(1) == 'tst' else evaluate(m.group(3), lang) & ((1 << 8 * size) - 1)
                have = int.from_bytes(hunks[h]['data'][at:at + size], 'big')
                if want != have:
                    bad.append('src/%s:%d %s: %0*x, the game has %0*x'
                               % (name, n, lang.name if lang else 'en', 2 * size, want, 2 * size, have))
    return count, bad


def parse_ref(s):
    if s.startswith('a4:'):
        return 11, (int(s[3:], 0) + 0x8000) & 0xffff
    h, o = s.split(':')
    return int(h.lstrip('h')), int(o, 16)


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    vs = [Version('de'), Version('fr')]
    if sys.argv[1] == 'summary':
        for v in vs:
            for h in CODE:
                m = v.code[h]
                shifts = []
                for x, y in m:
                    if not shifts or shifts[-1][1] != y - x:
                        shifts.append((x, y - x))
                if len(shifts) > 1 or shifts[0][1]:
                    print(v.name, 'h%d' % h, ' '.join('%05x:%+d' % s for s in shifts))
            print(v.name, 'h11 bss %+d' % v.bss)
    elif sys.argv[1] == 'symbols':
        text = symbols_text(vs)
        if '--check' in sys.argv:
            if not os.path.exists(OFFSETS) or open(OFFSETS).read() != text:
                raise SystemExit('src/offsets.s is out of date: python3 tools/versions.py symbols')
            print('src/offsets.s is up to date')
        else:
            open(OFFSETS, 'w').write(text)
            print('src/offsets.s: %d symbols' % text.count('= LOV_EN'))
    elif sys.argv[1] == 'check':
        if open(OFFSETS).read() != symbols_text(vs):
            raise SystemExit('src/offsets.s is out of date: python3 tools/versions.py symbols')
        count, bad = check_signatures(vs)
        if bad:
            raise SystemExit('signatures that do not hold:\n  ' + '\n  '.join(bad))
        print('src/offsets.s is current; %d signatures hold in English, German and French' % count)
    elif sys.argv[1] == 'map':
        for s in sys.argv[2:]:
            h, o = parse_ref(s)
            row = ['h%d:%05x' % (h, o)]
            for v in vs:
                f, how = v.map(h, o)
                row.append('%s=%s(%s)' % (v.name, '%05x' % f if f is not None else '-', how))
            print(' '.join(row))


if __name__ == '__main__':
    main()
