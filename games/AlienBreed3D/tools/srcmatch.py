"""Find the published AB3D I source's routines in the game executable.

    python3 tools/srcmatch.py SRC.s ... [> tmp/srcmatch.txt]

SRC are files of the AB3D I source (Agrigaatti/Alien-Breed-3D-I on GitHub), read from an
ignored tmp/ directory: it was released for personal use only, so it never enters the
repository. The executable is tmp/exe/abd.flat (tools/exe.py; FLAT= overrides).

The source is a development tree, not this build, so labels are matched by shape: each
global label's first 24 instructions become tokens (mnemonic and size, with the aliases an
assembler picks folded: addq/addi/adda are add, moveq is move.l; register operands kept, the
rest reduced to #, abs, (An) and so on) and vote, by 4-token n-grams, for a place in the
disassembly. A file's labels keep their source order, so the chosen places are the best
increasing chain. Prints per label: name, file:line, game offset, tokens equal/compared, and
`unique` (no other place scores as well) or `ordered` (chosen by the order).
"""
import os
import re
import subprocess
import sys
from collections import defaultdict

GAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAT = os.environ.get('FLAT') or os.path.join(GAME, 'tmp/exe/abd.flat')

NOSIZE = {'lea', 'pea', 'moveq', 'exg', 'swap', 'jsr', 'jmp', 'rts', 'nop', 'rte', 'unlk',
          'link', 'bsr', 'bra', 'dbf', 'illegal', 'trap', 'stop', 'reset', 'movem'}
BR = re.compile(r'^(b(ra|sr|hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le|hs|lo)|db[a-z]+)$')
ALIAS = {'addi': 'add', 'addq': 'add', 'adda': 'add', 'subi': 'sub', 'subq': 'sub',
         'suba': 'sub', 'cmpi': 'cmp', 'cmpa': 'cmp', 'movea': 'move', 'andi': 'and',
         'ori': 'or', 'eori': 'eor', 'dbra': 'dbf', 'bhs': 'bcc', 'blo': 'bcs'}
REG = re.compile(r'^(d[0-7]|a[0-7]|sp)$')


def split_ops(s):
    out, depth, cur = [], 0, ''
    for c in s:
        if c in '([':
            depth += 1
        elif c in ')]':
            depth -= 1
        if c == ',' and depth == 0:
            out.append(cur)
            cur = ''
        else:
            cur += c
    if cur:
        out.append(cur)
    return out


def opclass(o):
    o = o.strip().lower().replace('sp', 'a7')
    if REG.match(o):
        return o
    if o.startswith('#'):
        return '#'
    if re.match(r'^-\((a[0-7])\)$', o):
        return o
    if re.match(r'^\((a[0-7])\)\+?$', o):
        return o
    if '/' in o or re.match(r'^[ad][0-7]-[ad][0-7]', o):
        return 'list'
    if 'pc' in o:
        return 'abs'
    regs = re.findall(r'\b([ad][0-7])\b', o)
    if '(' in o and regs:
        return '(' + ','.join(regs) + ')'
    return 'abs'


def token(mn, ops):
    mn = mn.lower()
    if re.match(r'^db[a-z]\.s$', mn):        # objdump's dbcs, dbls, ...
        mn = mn.replace('.', '')
    base, _, size = mn.partition('.')
    base = ALIAS.get(base, base)
    if base == 'moveq':
        base, size = 'move', 'l'
    if BR.match(base) or base in NOSIZE:
        size = ''
    elif not size:
        size = 'w'
    cls = [opclass(o) for o in split_ops(ops)] if ops else []
    if base == 'move' and cls and cls[0] == '#':
        cls[0] = '#'
    if BR.match(base) or base in ('jsr', 'jmp', 'bsr'):
        cls = [c for c in cls if REG.match(c)]  # targets differ
    return base + ('.' + size if size else '') + ' ' + ','.join(cls)


def objdump(start=None, stop=None):
    args = ['m68k-amiga-elf-objdump', '-D', '-b', 'binary', '-m', 'm68k:68020']
    if start is not None:
        args += [f'--start-address={start}', f'--stop-address={stop}']
    return subprocess.run(args + [FLAT], capture_output=True, text=True, check=True).stdout


def dis_tokens(text):
    toks = []
    for line in text.splitlines():
        m = re.match(r'^\s*([0-9a-f]+):\t[0-9a-f ]+\t(\S+)\s*(.*)$', line)
        if not m:
            continue
        mn, ops = m.group(2), m.group(3)
        if mn.startswith('.'):
            toks.append((int(m.group(1), 16), '?'))
            continue
        ops = re.sub(r'(\w+)\.([wl]):(\d)', r'\1', ops)   # index scale
        toks.append((int(m.group(1), 16), token(mn, ops)))
    return toks


DIRECTIVE = {'dc', 'ds', 'dcb', 'equ', 'set', 'include', 'incbin', 'incdir', 'opt', 'ifnd',
             'ifd', 'ifeq', 'ifne', 'else', 'endc', 'even', 'cnop', 'section', 'xdef', 'xref',
             'macro', 'endm', 'rs', 'rsreset', 'rsset', 'align', 'printt', 'printv', 'equr',
             'end', 'ifgt', 'iflt', 'ifge', 'ifle', 'rept', 'endr', 'list', 'nolist'}
MNEM = re.compile(r'^[a-z]+(\.[bwls])?$')


def src_labels(path):
    """[(label, line, [tokens])]: global labels with up to 24 instructions after them."""
    lines = open(path, encoding='latin-1').read().splitlines()
    labs, cur = [], None
    for n, raw in enumerate(lines, 1):
        s = raw.split(';')[0].rstrip()
        if not s or s.lstrip().startswith('*'):
            continue
        m = re.match(r'^([A-Za-z_.][\w.]*):?(\s+(.*))?$', s) if not s[0].isspace() else None
        rest = s.strip()
        if m:
            name, rest = m.group(1), (m.group(3) or '').strip()
            if not name.startswith('.'):
                cur = [name, n, []]
                labs.append(cur)
            if not rest:
                continue
        w = rest.split(None, 1)
        mn = w[0].lower()
        if mn.split('.')[0] in DIRECTIVE or not MNEM.match(mn):
            if mn.split('.')[0] in ('dc', 'ds', 'incbin', 'dcb'):
                cur = None   # data: stop collecting for this label
            continue
        if cur is not None and len(cur[2]) < 24:
            cur[2].append(token(mn, w[1] if len(w) > 1 else ''))
    return [l for l in labs if len(l[2]) >= 6]


def fix_start(data, addr, st, same):
    """A CNOP pad word before a label joins the next opcode into one ori.b in the linear
    sweep: try 2 bytes on."""
    if data[addr:addr + 2] != b'\0\0':
        return addr, same
    alt = [t for _, t in dis_tokens(objdump(addr + 2, addr + 2 + 10 * len(st)))][:len(st)]
    s2 = sum(1 for a, b in zip(alt, st) if a == b)
    return (addr + 2, s2) if s2 > same else (addr, same)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    data = open(FLAT, 'rb').read()
    toks = dis_tokens(objdump())
    seq = [t for _, t in toks]
    K = 4
    index = defaultdict(list)
    for i in range(len(seq) - K):
        index[tuple(seq[i:i + K])].append(i)
    for path in sys.argv[1:]:
        rows = []
        for name, line, st in src_labels(path):
            votes = defaultdict(int)
            for j in range(len(st) - K + 1):
                hits = index.get(tuple(st[j:j + K]), [])
                if len(hits) > 50:
                    continue
                for i in hits:
                    votes[i - j] += 1
            cands = []
            for i0, v in votes.items():
                if 0 <= i0 < len(seq):
                    same = sum(1 for j, t in enumerate(st) if i0 + j < len(seq) and seq[i0 + j] == t)
                    cands.append((i0, same, v))
            cands.sort(key=lambda c: -c[1])
            rows.append((name, line, st, cands[:12]))
        # weighted longest increasing chain: labels keep their source order
        best = []  # per row: list of (score, prev_row, prev_cand) per candidate
        for r, (_, _, st, cands) in enumerate(rows):
            entry = []
            for ci, (i0, same, v) in enumerate(cands):
                w = same / len(st) if same / len(st) >= .5 else 0
                b = (w, None, None)
                for pr in range(r - 1, max(-1, r - 40), -1):
                    for pc, (sc, _, _) in enumerate(best[pr]):
                        if rows[pr][3][pc][0] < i0 and sc + w > b[0]:
                            b = (sc + w, pr, pc)
                entry.append(b)
            best.append(entry)
        chosen = {}
        r, c = None, None
        top = max(((sc[0], ri, ci) for ri, e in enumerate(best) for ci, sc in enumerate(e)), default=None)
        if top:
            _, r, c = top
            while r is not None:
                chosen[r] = c
                _, r, c = best[r][c][0], best[r][c][1], best[r][c][2]
        for r, (name, line, st, cands) in enumerate(rows):
            f = path.split('/')[-1]
            if r in chosen and cands[chosen[r]][1] / len(st) >= .5:
                i0, same, v = cands[chosen[r]]
                alts = sum(1 for c in cands if c[1] == same)
                at, same = fix_start(data, toks[i0][0], st, same)
                print(f'{name}\t{f}:{line}\t${at:05x}\t{same}/{len(st)}\t{"unique" if alts == 1 else "ordered"}')
            else:
                print(f'{name}\t{f}:{line}\t-\t{cands[0][1] if cands else 0}/{len(st)}')


if __name__ == '__main__':
    main()
