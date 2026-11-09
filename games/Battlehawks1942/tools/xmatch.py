#!/usr/bin/env python3
"""Translate Their Finest Hour's work to Battlehawks 1942: code the two games share.

  python3 tools/xmatch.py runs                  matched instruction runs (bh: <- bob:)
  python3 tools/xmatch.py sites [FILE.s ...]    TFH patch-list sites mapped to bh: offsets
                                                (default: TFH's src/*.s)
  python3 tools/xmatch.py site BOB_OFFSET ...   one bob: offset to bh: (exact or fuzzy)
  python3 tools/xmatch.py globals [OFFSET ...]  TFH a4 globals paired with BH's
  python3 tools/xmatch.py consts                immediates that differ in matched code
  python3 tools/xmatch.py jt [A4_OFFSET ...]    BH's jump table: jsr d16(a4) -> bh: offset
  python3 tools/xmatch.py dis START END         BH hunk-0 listing of bh:START..END (hex)

Both games are Aztec C from the same code base.  Each hunk 0 is disassembled with objdump
(m68k:68000) and the listings compared instruction by instruction, with addresses, offsets
and immediates outside -8..16 masked (registers and addressing modes kept).  A run is a
maximal sequence of equal normalised instructions, at least MINRUN long; inside a run the
instructions correspond one to one, so a bob: offset there maps to a bh: offset, and the
a4 offsets and immediates of corresponding instructions pair up (TFH's T 11700(a4) is BH's
10184(a4)).  A site outside every run is matched fuzzily (a window of instructions against
BH's, by difflib ratio): GOOD (>= 0.8) needs a look, WEAK and NONE need doing by hand.

Inputs: BH from the installed Disk.1 (`make unpack`), TFH's data/bob v1.1 from the
TheirFinestHour game directory beside this one (its own `make unpack`).  Both are checked
against their SHA-256.  Listings and results are cached in tmp/xmatch/.
"""
import bisect, collections, difflib, hashlib, json, os, re, struct, subprocess, sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401,E402

ROOT = Path(__file__).resolve().parents[1]
TFH_ROOT = ROOT.parent / 'TheirFinestHour'
CACHE = ROOT / 'tmp/xmatch'
BH_DISK = ROOT / 'tmp/game/Battlehawks1942/Disk.1'
BH_SHA = '0c952cd48c8aa67eb8748831685ecfc312c2982eba4fd3d27233feec3dc6ae05'
TFH_EXE = TFH_ROOT / 'tmp/game/TheirFinestHour/data/BOB'
TFH_SHA = '4b5931c8500e60b5f4cdbfa7f8e37930c731c14443bd1f88757090fb22443877'
A4 = 0x7FFE                      # Aztec small data: a4 = data hunk + $7FFE
K, MINRUN, WINDOW = 10, 12, 14

LINE = re.compile(r'^\s*([0-9a-f]+):\t([0-9a-f ]+?)\s*\t(\S+)\s*(.*)$')
A4REF = re.compile(r'(-?\d+)\(a4\)')
IMM = re.compile(r'#(-?\d+)')


def die(msg):
    sys.exit(f'xmatch: {msg}')


# ---- inputs --------------------------------------------------------------------------

def hunks(data):
    """Amiga load file -> list of (type, bytes, {target hunk: [offsets]})."""
    def l(o):
        return struct.unpack_from('>I', data, o)[0]
    if l(0) != 0x3F3:
        die('not a load file')
    o = 4
    while l(o):                       # resident library names
        o += 4 + 4 * l(o)
    o += 4
    n = l(o + 8) - l(o + 4) + 1
    o += 12 + 4 * n
    out = []
    while o < len(data) and len(out) < n:
        t = l(o) & 0x3FFFFFFF
        if t in (0x3E9, 0x3EA):
            size = 4 * l(o + 4)
            out.append([t, data[o + 8:o + 8 + size], {}])
            o += 8 + size
        elif t == 0x3EB:
            out.append([t, b'', {}])
            o += 8
        elif t == 0x3EC:
            o += 4
            while l(o):
                cnt, tgt = l(o), l(o + 4)
                out[-1][2].setdefault(tgt, []).extend(l(o + 8 + 4 * i) for i in range(cnt))
                o += 8 + 4 * cnt
            o += 4
        elif t == 0x3F0:                # symbols
            o += 4
            while l(o):
                o += 8 + 4 * (l(o) & 0xFFFFFF)
            o += 4
        elif t == 0x3F2:
            o += 4
        else:
            die(f'unknown hunk type ${t:x}')
    return out


def checked(path, sha, how):
    if not path.is_file():
        die(f'{path} is missing ({how})')
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        die(f'{path} differs from the version this tool knows')
    return data


def bh_exe():
    exe = CACHE / 'BH'
    if not exe.is_file():
        if not BH_DISK.is_file():
            die(f'{BH_DISK} is missing (make unpack)')
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run([sys.executable, '-m', 'amigaxdev.adf', str(BH_DISK), 'BH', str(exe)],
                       check=True, stdout=subprocess.DEVNULL)
    return checked(exe, BH_SHA, 'make unpack')


def tfh_exe():
    return checked(TFH_EXE, TFH_SHA, 'make unpack in games/TheirFinestHour')


def listing(name, code):
    """objdump of a hunk-0 image, cached; -> [(addr, normalised, text)]"""
    CACHE.mkdir(parents=True, exist_ok=True)
    binf, dis = CACHE / f'{name}0.bin', CACHE / f'{name}0.dis'
    if not binf.is_file() or binf.read_bytes() != code:
        binf.write_bytes(code)
        dis.unlink(missing_ok=True)
    if not dis.is_file():
        with open(dis, 'w') as f:
            subprocess.run(['m68k-amiga-elf-objdump', '-D', '-b', 'binary', '-m', 'm68k:68000',
                            str(binf)], check=True, stdout=f)
    out = []
    for ln in open(dis):
        m = LINE.match(ln)
        if not m:
            continue
        mn, ops = m.group(3), m.group(4)
        norm = IMM.sub(lambda x: x.group(0) if -8 <= int(x.group(1)) <= 16 else '#N', ops)
        norm = re.sub(r'(?<![#\w])-?(0x[0-9a-f]+|\d+)', 'N', norm)
        out.append((int(m.group(1), 16), f'{mn} {norm}', f'{mn} {ops}'.rstrip()))
    return out


class Match:
    def __init__(self):
        self.bh_hunks = hunks(bh_exe())
        self.A = listing('bh', self.bh_hunks[0][1])
        self.B = listing('bob', hunks(tfh_exe())[0][1])
        self.aidx = {x[0]: n for n, x in enumerate(self.A)}
        self.bidx = {x[0]: n for n, x in enumerate(self.B)}
        self.runs = self._runs()

    def _runs(self):
        ta, tb = [x[1] for x in self.A], [x[1] for x in self.B]
        idx = collections.defaultdict(list)
        for j in range(len(tb) - K + 1):
            idx[tuple(tb[j:j + K])].append(j)
        cand = []
        for i in range(len(ta) - K + 1):
            for j in idx.get(tuple(ta[i:i + K]), ()):
                if i and j and ta[i - 1] == tb[j - 1]:
                    continue                    # inside a longer run
                n = K
                while i + n < len(ta) and j + n < len(tb) and ta[i + n] == tb[j + n]:
                    n += 1
                if n >= MINRUN:
                    cand.append((n, i, j))
        cand.sort(reverse=True)
        covered = bytearray(len(ta))
        runs = []
        for n, i, j in cand:                    # longest first, BH instructions used once
            if any(covered[i:i + n]):
                continue
            covered[i:i + n] = b'\1' * n
            runs.append((i, j, n))
        runs.sort()
        return runs

    def pairs(self):
        """corresponding (BH instruction, TFH instruction) pairs in every run"""
        for i, j, n in self.runs:
            for t in range(n):
                yield self.A[i + t], self.B[j + t]

    def site(self, b):
        """bob: offset -> ('exact', bh) or (GOOD/WEAK/NONE, bh or None, ratio)"""
        for i, j, n in self.runs:
            b0 = self.B[j][0]
            b1 = self.B[j + n][0] if j + n < len(self.B) else self.B[j + n - 1][0] + 2
            if b0 <= b < b1:
                return ('exact', self.A[i][0] + b - b0, 1.0)
        return self.fuzzy(b)

    def fuzzy(self, b):
        if not hasattr(self, '_tri'):
            ta = [x[1] for x in self.A]
            self._tri = collections.defaultdict(set)
            for i in range(len(ta) - 2):
                self._tri[tuple(ta[i:i + 3])].add(i)
            self._baddr = [x[0] for x in self.B]
        ta = [x[1] for x in self.A]
        j = bisect.bisect_left(self._baddr, b)
        win = [x[1] for x in self.B[j:j + WINDOW]]
        votes = collections.Counter()
        for k in range(len(win) - 2):
            for i in self._tri.get(tuple(win[k:k + 3]), ()):
                if i >= k:
                    votes[i - k] += 1
        best = (0.0, None)
        for i, _ in votes.most_common(40):
            r = difflib.SequenceMatcher(None, win, ta[i:i + WINDOW], autojunk=False).ratio()
            if r > best[0]:
                best = (r, i)
        r, i = best
        tag = 'GOOD' if r >= 0.8 else 'WEAK' if r >= 0.6 else 'NONE'
        return (tag, self.A[i][0] + (b - self.B[j][0]) if i is not None else None, r)

    def globals(self):
        g = collections.defaultdict(collections.Counter)
        for a, b in self.pairs():
            for x, y in zip(A4REF.findall(b[2]), A4REF.findall(a[2])):
                g[int(x)][int(y)] += 1
        return {k: (c.most_common(1)[0][0], c.most_common(1)[0][1], len(c))
                for k, c in sorted(g.items())}

    def jump_table(self):
        """a4 offset -> bh: offset, from the data hunk's `jmp abs.l` entries"""
        data = self.bh_hunks[1][1]
        reloc0 = set(self.bh_hunks[1][2].get(0, ()))
        out = {}
        for o in range(0, min(len(data), A4) - 5, 2):
            if data[o:o + 2] == b'\x4e\xf9' and o + 2 in reloc0:
                out[o - A4] = struct.unpack_from('>I', data, o + 2)[0]
        return out


# ---- commands ------------------------------------------------------------------------

def cmd_runs(m, _):
    total = sum(n for _, _, n in m.runs)
    print(f'# {len(m.runs)} runs, {total} of {len(m.A)} BH instructions '
          f'({100 * total / len(m.A):.1f}%) in runs of {MINRUN} or more')
    for i, j, n in m.runs:
        print(f'bh:{m.A[i][0]:05x}..{m.A[i + n - 1][0]:05x}  '
              f'bob:{m.B[j][0]:05x}..{m.B[j + n - 1][0]:05x}  {n}')


PL = re.compile(r'^\s*(PL_[A-Z]+)\s+\$([0-9a-f]+)\s*,?\s*([^;\s]*)', re.I)


def cmd_sites(m, args):
    files = args or sorted(str(p) for p in (TFH_ROOT / 'src').glob('*.s'))
    tally = collections.Counter()
    for f in files:
        for ln, line in enumerate(open(f), 1):
            mm = PL.match(line)
            if not mm or mm.group(1).upper() == 'PL_NOP':
                continue
            b = int(mm.group(2), 16)
            tag, a, r = m.site(b)
            tally[tag] += 1
            where = f'bh:{a:05x}' if a is not None else '-'
            print(f'{tag:5s} {r:.2f} bob:{b:05x} -> {where:9s} {Path(f).name}:{ln} '
                  f'{mm.group(1)} {mm.group(3)}')
    print('# ' + ', '.join(f'{k} {v}' for k, v in tally.most_common()))


def cmd_site(m, args):
    for s in args:
        tag, a, r = m.site(int(s, 16))
        print(f'bob:{int(s, 16):05x} -> ' + (f'bh:{a:05x}' if a is not None else '-')
              + f' {tag} {r:.2f}')


def cmd_globals(m, args):
    g = m.globals()
    amb = sum(1 for v in g.values() if v[2] > 1)
    if not args:
        print(f'# {len(g)} TFH globals paired, {amb} with more than one BH partner')
        print('# TFH(a4)  BH(a4)  uses  partners')
        for k, (a, n, c) in g.items():
            print(f'{k:7d} {a:7d} {n:5d} {c:3d}')
    for s in args:
        v = g.get(int(s))
        print(f'{s} -> ' + (f'{v[0]}(a4) ({v[1]} uses, {v[2]} partner(s))' if v else '-'))


def cmd_consts(m, _):
    pairs, where, same = collections.Counter(), {}, 0
    for a, b in m.pairs():
        for p, q in zip(IMM.findall(b[2]), IMM.findall(a[2])):
            if p == q:
                same += 1
            else:
                pairs[(int(p), int(q))] += 1
                where.setdefault((int(p), int(q)), a[0])
    print(f'# {same} equal immediates, {sum(pairs.values())} differing '
          f'({len(pairs)} distinct pairs)')
    for (p, q), n in pairs.most_common():
        print(f'TFH #{p:<7} BH #{q:<7} x{n:<3} first bh:{where[(p, q)]:05x}')


def cmd_jt(m, args):
    jt = m.jump_table()
    for k in (map(int, args) if args else sorted(jt)):
        print(f'{k:7d}(a4) -> ' + (f'bh:{jt[k]:05x}' if k in jt else '-'))


def cmd_dis(m, args):
    s, e = int(args[0], 16), int(args[1], 16)
    for a, _, text in m.A:
        if s <= a < e:
            print(f'{a:6x}  {text}')


COMMANDS = {'runs': cmd_runs, 'sites': cmd_sites, 'site': cmd_site, 'globals': cmd_globals,
            'consts': cmd_consts, 'jt': cmd_jt, 'dis': cmd_dis}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](Match(), sys.argv[2:])
