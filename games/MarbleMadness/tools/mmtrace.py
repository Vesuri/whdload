"""Static and trace analysis of Marble Madness at PatchSeg offsets.

    python3 tools/mmtrace.py image                 tmp/ana/mm.bin(.json): the hunks at their PatchSeg
                                                   offsets, RELOC32 applied, so addresses = offsets
    python3 tools/mmtrace.py ghidra                import tmp/ana/mm.bin into Ghidra: listing.txt,
                                                   listing.named.txt (library calls named), callgraph.txt
    python3 tools/mmtrace.py segmap DUMP [BASE]    runtime address of every hunk from a memory dump
                                                   (`marblemadness.py dump`), via the Framer task and
                                                   the seglist; writes DUMP.segmap.json
    python3 tools/mmtrace.py split MAP TRACE...    cycles per field by task (stack ranges), supervisor, idle
    python3 tools/mmtrace.py tree MAP TASK DEPTH TRACE...
                                                   inclusive call tree of one task
    python3 tools/mmtrace.py count MAP OFF[,OFF..] TRACE...
                                                   entries per field to each PatchSeg offset

MAP is a DUMP.segmap.json. The layout differs by setup (fast memory, or chip RAM only on
`a1200`), so map each trace with a dump from the same run. Offsets are hex.
"""
import bisect
import collections
import json
import os
import re
import struct
import subprocess
import sys
from pathlib import Path

GAME = Path(__file__).resolve().parents[1]
sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or os.path.expanduser('~/.local/share/amiga/pylib'))
EXE = GAME / 'tmp/game/MarbleMadness/data/MarbleMadness!'
ANA = GAME / 'tmp/ana'
IMG = ANA / 'mm.bin'
TASKS = (('Framer', 0x7058), ('Painter', 0x94BC), ('Scroller', 0xAB1C), ('music', 0x1FA82),
         ('SfxTask', 0x21170))
FRAMER_NAME = 0x70D8 - 0x7058      # ln_Name string inside hunk 34
IDLE = (0x2CF0, 0x2D00)            # the idle task's loop (patched to key_control)


def be32(d, o):
    return struct.unpack_from('>I', d, o)[0]


# -- the flat image ------------------------------------------------------------------------------

def cmd_image(args):
    exe = EXE.read_bytes()
    o = 4
    while be32(exe, o):
        o += 4 + 4 * be32(exe, o)
    first, last = be32(exe, o + 8), be32(exe, o + 12)
    o += 16
    sizes = [(be32(exe, o + 4 * i) & 0x3FFFFFFF) * 4 for i in range(last - first + 1)]
    o += 4 * len(sizes)
    bases = [sum(sizes[:i]) for i in range(len(sizes))]
    img = bytearray(sum(sizes))
    hunks, cur = [], -1
    kinds = {0x3E9: 'CODE', 0x3EA: 'DATA', 0x3EB: 'BSS'}
    while o < len(exe):
        t = be32(exe, o) & 0x3FFFFFFF
        if t in kinds:
            cur += 1
            n = be32(exe, o + 4)
            if t != 0x3EB:
                img[bases[cur]:bases[cur] + 4 * n] = exe[o + 8:o + 8 + 4 * n]
                o += 8 + 4 * n
            else:
                o += 8
            hunks.append({'i': cur, 'type': kinds[t], 'base': bases[cur], 'size': sizes[cur]})
        elif t == 0x3EC:
            o += 4
            while be32(exe, o):
                k, th = be32(exe, o), be32(exe, o + 4)
                o += 8
                for j in range(k):
                    a = bases[cur] + be32(exe, o + 4 * j)
                    struct.pack_into('>I', img, a, (be32(img, a) + bases[th]) & 0xFFFFFFFF)
                o += 4 * k
            o += 4
        elif t == 0x3F2:
            o += 4
        else:
            sys.exit(f'hunk type {t:x} at {o:x}')
    ANA.mkdir(parents=True, exist_ok=True)
    IMG.write_bytes(img)
    Path(str(IMG) + '.json').write_text(json.dumps(hunks))
    print(f'{IMG}: {len(hunks)} hunks, {len(img):#x} bytes')


def cmd_ghidra(args):
    ghidra = sorted(Path(os.path.expanduser('~/.local/share/ghidra')).glob('ghidra_*_PUBLIC'))[-1]
    env = dict(os.environ, JAVA_HOME=os.environ.get('JAVA_HOME', '/opt/homebrew/opt/openjdk@21'))
    proj = ANA / 'proj'
    subprocess.run(['rm', '-rf', str(proj)], check=True)
    proj.mkdir(parents=True)
    scripts = f"{GAME / 'tools/ghidra'};{os.environ.get('AMIGA_GHIDRA_SCRIPTS', '')}"
    subprocess.run([str(ghidra / 'support/analyzeHeadless'), str(proj), 'mm', '-import', str(IMG),
                    '-processor', '68000:BE:32:default', '-loader', 'BinaryLoader',
                    '-loader-baseAddr', '0', '-scriptPath', scripts,
                    '-preScript', 'MMSetup.java', str(IMG) + '.json',
                    '-postScript', 'ExportListing.java', str(ANA / 'listing.txt'),
                    '-postScript', 'DumpCallGraph.java', str(ANA / 'callgraph.txt')],
                   env=env, check=True, stdout=open(ANA / 'ghidra.log', 'w'), stderr=subprocess.STDOUT)
    name_calls()
    print(ANA / 'listing.named.txt')


def name_calls():
    """listing.named.txt: listing.txt with stub calls named from the NDK's FD files."""
    fd_dir = Path(os.path.expanduser('~/.local/share/amiga/ndk/FD'))

    def fd(name):
        out, bias = {}, 0
        for line in open(fd_dir / name):
            line = line.strip()
            if line.startswith('##bias'):
                bias = int(line.split()[1])
            elif line and not line.startswith(('##', '*')):
                out[bias] = line.split('(')[0]
                bias += 6
        return out
    libs = {0x1F4: fd('exec_lib.fd'), 0x1F8: fd('dos_lib.fd'), 0x7B1C: fd('graphics_lib.fd'),
            0x2CD4: fd('intuition_lib.fd')}
    listing = (ANA / 'listing.txt').read_text().splitlines()
    lines = [l for l in listing if re.match(r'[0-9a-f]{8} ', l)]
    names = {}
    for i, l in enumerate(lines):
        m = re.search(r'jsr \(-0x([0-9a-f]+),A6\)', l)
        if not m:
            continue
        for k in range(i - 1, max(i - 5, -1), -1):
            b = re.search(r'movea\.l \(0x([0-9a-f]+)\)\.l,A6', lines[k])
            if b:
                break
        else:
            continue
        k2 = k
        while k2 > 0 and 'rts' not in lines[k2 - 1]:
            k2 -= 1
        lib = libs.get(int(b.group(1), 16))
        if lib:
            names[int(lines[k2][:8], 16)] = lib.get(int(m.group(1), 16), '?')
    with open(ANA / 'listing.named.txt', 'w') as out:
        for l in listing:
            m = re.search(r'(jsr|jmp|bsr\.[bw]) 0x([0-9a-f]+)', l)
            if m and int(m.group(2), 16) in names:
                l += '   ; ' + names[int(m.group(2), 16)]
            out.write(l + '\n')


# -- runtime map ---------------------------------------------------------------------------------

def hunk_table():
    return json.loads(Path(str(IMG) + '.json').read_text())


def cmd_segmap(args):
    dump = Path(args[0])
    mem = dump.read_bytes()
    base = int(args[1], 16) if len(args) > 1 else 0
    hunks = hunk_table()
    L = lambda a: be32(mem, a - base)
    h34 = None
    for m in re.finditer(b'Framer\0', mem):
        a = base + m.start()
        if a - FRAMER_NAME >= base and L(a - FRAMER_NAME + 10) == a:
            h34 = a - FRAMER_NAME
    if h34 is None:
        sys.exit('no Framer task in the dump')
    addr = {34: h34}
    a = h34
    for i in range(35, len(hunks)):
        a = (L(a - 4) << 2) + 4
        addr[i] = a
    a = h34
    for i in range(33, -1, -1):
        want = struct.pack('>I', (a - 4) >> 2)
        sz = hunks[i]['size']
        hits = [p for p in range(4, len(mem) - 4, 4) if mem[p:p + 4] == want
                and be32(mem, p - 4) in (sz + 8, ((sz + 7) & ~7) + 8)]
        if len(hits) != 1:
            sys.exit(f'hunk {i}: {len(hits)} candidates')
        a = base + hits[0] + 4
        addr[i] = a
    img = IMG.read_bytes()
    bad = [h['i'] for h in hunks if h['type'] == 'CODE' and h['size'] >= 2
           and mem[addr[h['i']] - base:addr[h['i']] - base + 2] != img[h['base']:h['base'] + 2]]
    tasks = []
    for name, o in TASKS:
        t = to_rt(addr, hunks, o)
        tasks.append([name, L(t + 0x3A), L(t + 0x3E)])
    out = Path(str(dump) + '.segmap.json')
    out.write_text(json.dumps({'hunks': {h['i']: [addr[h['i']], h['base'], h['size']] for h in hunks},
                               'tasks': tasks}))
    print(f'{out}: hunk 0 at {addr[0]:#x}; code hunks whose first word differs: {bad}')


def to_rt(addr, hunks, o):
    for h in hunks:
        if h['base'] <= o < h['base'] + h['size']:
            return addr[h['i']] + o - h['base']
    raise ValueError(f'{o:#x} is in no hunk')


class Map:
    def __init__(self, path):
        m = json.loads(Path(path).read_text())
        self.rows = sorted((a, b, s) for a, b, s in m['hunks'].values() if s > 0)
        self.starts = [r[0] for r in self.rows]
        self.tasks = m['tasks']
        funcs = []
        listing = ANA / 'listing.txt'
        if listing.exists():
            for l in open(listing):
                f = re.match(r'; FUNC (\S+)\s+([0-9a-f]+) - ([0-9a-f]+)', l)
                if f:
                    funcs.append((int(f.group(2), 16), int(f.group(3), 16)))
        self.funcs = sorted(funcs)
        self.fstarts = [f[0] for f in self.funcs]

    def off(self, pc):
        i = bisect.bisect_right(self.starts, pc) - 1
        if i >= 0:
            a, b, s = self.rows[i]
            if pc < a + s:
                return b + pc - a
        return None

    def rt(self, o):
        for a, b, s in self.rows:
            if b <= o < b + s:
                return a + o - b
        raise ValueError(f'{o:#x} is in no hunk')

    def func(self, o):
        i = bisect.bisect_right(self.fstarts, o) - 1 if o is not None else -1
        return self.funcs[i][0] if i >= 0 and o <= self.funcs[i][1] else None

    def task(self, pc, sp, sr):
        if sr & 0x2000:
            return 'super'
        for name, lo, hi in self.tasks:
            if lo <= sp <= hi:
                return name
        o = self.off(pc)
        # outside every hunk on no task's stack: the slave's key_control on its own stack
        return 'idle' if o is None or IDLE[0] <= o < IDLE[1] else 'other'


def traces(paths):
    from amigaxdev import barto
    for p in paths:
        t = barto.load(p)
        for f in t.fields:
            yield t, f


def cmd_split(args):
    m = Map(args[0])
    tot, n = collections.Counter(), 0
    for t, f in traces(args[1:]):
        n += 1
        for pc, cost, r in t.instructions(f):
            tot[m.task(pc, r[15], r[16])] += cost
    allc = sum(tot.values())
    print(f'{n} fields, {allc // n} cycles a field')
    for k, c in tot.most_common():
        print(f'  {k:9s} {100 * c / allc:5.1f}%  {c // n:8d}/field')


def cmd_tree(args):
    m, name, depth = Map(args[0]), args[1], int(args[2])
    lo, hi = next((a, b) for t, a, b in m.tasks if t == name)
    inc, calls, n = collections.Counter(), collections.Counter(), 0
    stack, psp = [], None
    for t, f in traces(args[3:]):
        n += 1
        for pc, cost, r in t.instructions(f):
            sp = r[15]
            if r[16] & 0x2000 or not lo <= sp <= hi:
                continue
            o = m.off(pc)
            while stack and sp > stack[-1][1]:
                stack.pop()
            if psp is not None and sp == psp - 4 and o is not None and m.func(o) == o:
                stack.append((o, sp))
                if len(stack) <= depth:
                    calls[tuple(s[0] for s in stack)] += 1
            psp = sp
            path = tuple(s[0] for s in stack)
            for d in range(1, min(depth, len(path)) + 1):
                inc[path[:d]] += cost
    for k in sorted(inc):
        if inc[k] // n >= 300:
            print('  ' * (len(k) - 1) + f'${k[-1]:X}', inc[k] // n, 'cycles/field,', calls[k], 'entries')


def cmd_count(args):
    m = Map(args[0])
    offs = [int(x, 16) for x in args[1].split(',')]
    want = {m.rt(o): o for o in offs}
    for i, (t, f) in enumerate(traces(args[2:])):
        c = collections.Counter()
        for pc, cost, r in t.instructions(f):
            if pc in want:
                c[want[pc]] += 1
        print(i, ' '.join(f'${o:X}:{c[o]}' for o in offs))


if __name__ == '__main__':
    cmds = {'image': cmd_image, 'ghidra': cmd_ghidra, 'segmap': cmd_segmap, 'split': cmd_split,
            'tree': cmd_tree, 'count': cmd_count}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(__doc__)
    cmds[sys.argv[1]](sys.argv[2:])
