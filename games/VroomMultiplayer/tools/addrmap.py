"""Map Vroom program addresses to Vroom Multiplayer's (v1).

    addrmap.py VROOM.bin VMP.bin map ADDR ...   each address: code and data correspondence
    addrmap.py VROOM.bin VMP.bin segs           the aligned code: Vroom range, shift
    addrmap.py VROOM.bin VMP.bin data [LO HI]   the operand correspondences
    addrmap.py VROOM.bin VMP.bin cmp LO HI      the instructions side by side

Both images are chip memory from 0 at the program's entry ($3658, `BOOT_BREAK`), with the
original slaves' patches in. The two programs are the same code with data and variables
moved, so the alignment is on instructions: each image is decoded linearly (capstone) from
$3600, each instruction becomes a token of its mnemonic and operands with addresses and
branch targets left out, and the token sequences are aligned (unique 8-token runs as
anchors, the longest chain increasing in both, difflib between anchors). Aligned
instructions with equal tokens give the code correspondence; their differing absolute
operands and branch targets the data and code address pairs.

`map` gives a code address through the aligned instruction at or before it, and any
address through the operand pairs: the exact value's pair, else the shift its nearest
pairs below and above agree on.
"""
import sys, bisect, collections, difflib, re
import capstone

LO, HI = 0x3600, 0x40000
KG = 8
NUM = re.compile(r'\$([0-9a-f]+)')

def decode(m):
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    out = []
    pc = LO
    while pc < HI:
        got = False
        for ins in md.disasm(m[pc:HI], pc):
            out.append(ins)
            pc = ins.address + ins.size
            got = True
        if not got or pc < HI:
            pc += 2
    return out

def token(ins):
    """mnemonic and operands, numbers >= $1000 (addresses, branch targets) as '@'"""
    ops = NUM.sub(lambda mo: '$' + mo.group(1) if int(mo.group(1), 16) < 0x1000 else '@', ins.op_str)
    if ins.mnemonic.startswith(('b', 'db')) and not ins.mnemonic.startswith(('btst', 'bset', 'bclr', 'bchg')):
        ops = re.sub(r'\$[0-9a-f]+$', '@', ops)
    return ins.mnemonic.split('.')[0] + ' ' + ops

def nums(ins):
    return [int(x, 16) for x in NUM.findall(ins.op_str)]

def lis(pairs):
    tails, idx, prev = [], [], [None] * len(pairs)
    for n, (_, y) in enumerate(pairs):
        p = bisect.bisect_left(tails, y)
        if p == len(tails):
            tails.append(y); idx.append(n)
        else:
            tails[p] = y; idx[p] = n
        prev[n] = idx[p - 1] if p else None
    out, n = [], idx[-1] if idx else None
    while n is not None:
        out.append(pairs[n]); n = prev[n]
    return out[::-1]

def grams(t):
    d = {}
    for i in range(len(t) - KG):
        d.setdefault(tuple(t[i:i + KG]), []).append(i)
    return {k: v[0] for k, v in d.items() if len(v) == 1}

class Map:
    def __init__(self, a, b):
        self.ia, self.ib = decode(a), decode(b)
        ta = [token(i) for i in self.ia]; tb = [token(i) for i in self.ib]
        ga, gb = grams(ta), grams(tb)
        anch = lis(sorted((ga[k], gb[k]) for k in ga.keys() & gb.keys()))
        pairs = []  # aligned instruction index pairs
        pi, pj = 0, 0
        for i, j in anch + [(len(ta), len(tb))]:
            if i < pi or j < pj:
                continue
            if i - pi < 4000 and j - pj < 4000:
                sm = difflib.SequenceMatcher(None, ta[pi:i], tb[pj:j], autojunk=False)
                for x, y, n in sm.get_matching_blocks():
                    pairs += [(pi + x + k, pj + y + k) for k in range(n)]
            pairs += [(i + k, j + k) for k in range(KG) if i + k < len(ta) and j + k < len(tb)
                      and ta[i + k] == tb[j + k]]
            pi, pj = i + KG, j + KG
        seen = set(); self.pairs = []
        for p in pairs:
            if p not in seen and p[0] < len(ta):
                seen.add(p); self.pairs.append(p)
        self.pairs.sort()
        self.addr_a = [self.ia[i].address for i, _ in self.pairs]
        votes = collections.defaultdict(collections.Counter)
        for i, j in self.pairs:
            na, nb = nums(self.ia[i]), nums(self.ib[j])
            if len(na) == len(nb):
                for x, y in zip(na, nb):
                    if x >= 0x1000 and y >= 0x1000:
                        votes[x][y] += 1
        self.votes = votes
        self.keys = sorted(votes)

    def code(self, v):
        k = bisect.bisect_right(self.addr_a, v) - 1
        if k < 0:
            return None, None
        i, j = self.pairs[k]
        ia, ib = self.ia[i], self.ib[j]
        if v >= ia.address + ia.size:
            return None, None
        return ib.address + (v - ia.address), ia

    def data(self, v):
        if v in self.votes:
            c = self.votes[v].most_common()
            return c[0][0], f"x{c[0][1]}" + (" others " + ",".join(f"{y:X}x{n}" for y, n in c[1:4]) if len(c) > 1 else "")
        i = bisect.bisect_left(self.keys, v)
        ds = []
        for k in (self.keys[i - 1] if i else None, self.keys[i] if i < len(self.keys) else None):
            if k is not None:
                ds.append((k, self.votes[k].most_common(1)[0][0] - k))
        if len(ds) == 2 and ds[0][1] == ds[1][1]:
            return v + ds[0][1], f"between {ds[0][0]:X}-{ds[1][0]:X}"
        return None, "near " + ", ".join(f"{k:X}{d:+X}" for k, d in ds)

    def segs(self):
        out = []
        for i, j in self.pairs:
            a, b = self.ia[i].address, self.ib[j].address
            if out and out[-1][2] == b - a:
                out[-1][1] = a + self.ia[i].size
            else:
                out.append([a, a + self.ia[i].size, b - a])
        return out

def main():
    a = open(sys.argv[1], 'rb').read(); b = open(sys.argv[2], 'rb').read()
    m = Map(a, b)
    cmd = sys.argv[3]
    if cmd == 'segs':
        for s, e, d in m.segs():
            print(f"{s:06X}-{e:06X} d={d:+X}")
    elif cmd == 'map':
        for s in sys.argv[4:]:
            v = int(s, 16)
            c, ins = m.code(v)
            dv, how = m.data(v)
            cs = f"{c:06X}" if c is not None else "-"
            ds = f"{dv:06X}" if dv is not None else "-"
            print(f"{v:06X}: code {cs:>6}  data {ds:>6} ({how})" +
                  (f"  [{ins.mnemonic} {ins.op_str}]" if ins else ""))
    elif cmd == 'data':
        lo = int(sys.argv[4], 16) if len(sys.argv) > 4 else 0
        hi = int(sys.argv[5], 16) if len(sys.argv) > 5 else 1 << 32
        for k in m.keys:
            if lo <= k < hi:
                print(f"{k:06X} " + " ".join(f"{y:06X}x{n}" for y, n in m.votes[k].most_common()))
    elif cmd == 'cmp':
        lo, hi = int(sys.argv[4], 16), int(sys.argv[5], 16)
        al = dict(m.pairs)
        for i, ins in enumerate(m.ia):
            if lo <= ins.address < hi:
                j = al.get(i)
                r = m.ib[j] if j is not None else None
                print(f"{ins.address:06X} {ins.mnemonic:8} {ins.op_str:34} | " +
                      (f"{r.address:06X} {r.mnemonic:8} {r.op_str}" if r else "-"))

if __name__ == '__main__':
    main()
