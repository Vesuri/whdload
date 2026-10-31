#!/usr/bin/env python3
"""F2: F1GP-Ed's writes against the slave's patches, hooks, tables and the state it names.

  python3 tools/f2_collisions.py DIR... [--near N] [--report tmp/f2/report.json]

Each DIR holds f1gp files saved by F1GP-Ed (F1: tmp/f1/out, tmp/f1/chunk, tmp/f1/byte).
The write set is every hunk byte and relocation that differs from the pinned file in any
of them. Against it:
- patches: every PL_* site of patch_582992, its _options and _clock, a hook extended to
  the continuation the slave jumps back to (c2_target_*);
- names: every other hexadecimal literal in the slave that may be a hunk 0 or 2 offset
  (entries it calls, tables of state ranges, displacements from the hunk bases), as the
  window [value, value+N) in both hunks (over-approximate: hits are reviewed by hand);
- E2/E4: tools/e2_tables.py and tools/e4_tables.py rerun on each distinct edited file;
  differences from the stock file's tables, which the slave was built from, are grouped
  by kind. The descent also starts at the original entry, which F1GP-Ed's startup hook
  reaches through a computed jump.
The output names hunk offsets only; the report must stay under tmp/.
"""
import argparse, collections, hashlib, json, os, re, struct, sys
from pathlib import Path
import numpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1_diff                                                    # noqa: E402
from slave_inputs import ROOT                                     # noqa: E402

PINNED = ROOT/'tmp/game/FormulaOneGrandPrix4Disk/data/f1gp'
SOURCE = ROOT/'whdload/F1GP.s'
LENGTH = {'PL_L': 4, 'PL_W': 2, 'PL_B': 1, 'PL_P': 6, 'PL_PS': 6, 'PL_R': 2}
LISTS = ('patch_582992', 'patch_582992_options', 'patch_582992_clock')
ENTRY = 0x88e                    # the stock entry JMP's target


def sizes(f):
    """Hunk sizes from the load file's header (BSS hunks included)."""
    o = 4
    while struct.unpack_from('>I', f, o)[0]:
        o += 4 + 4*struct.unpack_from('>I', f, o)[0]
    n, first, last = struct.unpack_from('>III', f, o+4)
    return [4*(struct.unpack_from('>I', f, o+16+4*k)[0] & 0x3fffffff) for k in range(last-first+1)]


def seg(size, offset):
    """(hunk, offset) of a resload_PatchSeg offset (hunk data counted back to back)."""
    for h, n in enumerate(size):
        if offset < n:
            return h, offset
        offset -= n
    raise ValueError('offset beyond the segments')


def writes(dirs, pinned, layout):
    """{(hunk, offset): {file}} of changed bytes, {(hunk, offset): {file}} of changed
    relocations, and the distinct edited files."""
    stock, base = f1_diff.relocs(pinned), numpy.frombuffer(pinned, numpy.uint8)
    data, reloc, distinct = collections.defaultdict(set), collections.defaultdict(set), {}
    for d in dirs:
        for p in sorted(Path(d).glob('*.f1gp')):
            f = p.read_bytes()
            if len(f) != len(pinned) or f == pinned:
                continue
            name = f'{Path(d).name}/{p.stem}'
            distinct.setdefault(hashlib.sha256(f).hexdigest(), (name, p))
            for i in numpy.flatnonzero(numpy.frombuffer(f, numpy.uint8) != base):
                h, o = f1_diff.where(layout, int(i))
                if h is not None:
                    data[(h, o)].add(name)
            edited = f1_diff.relocs(f)
            for k in stock.keys() | edited.keys():
                if stock.get(k) != edited.get(k):
                    reloc[k].add(name)
    return data, reloc, list(distinct.values())


def slave(size):
    """PL sites [(hunk, low, high, line, text)], continuation targets and literals."""
    lines = SOURCE.read_text().splitlines()
    sites, literals, current = [], [], None
    targets, table = set(), None
    for n, line in enumerate(lines, 1):
        code = line.split(';')[0]
        words = code.split()
        if words[:1] and not line[:1].isspace():
            current = words[0] if words[0] in LISTS else (None if words[0].startswith('patch_') else current)
            table = {'c2_target_h0': 0, 'c2_target_h2': 2}.get(words[0], table)
            if words[0] == 'c2_target_end':
                table = None
            m = re.match(r'\w+\s+dc\.l\s+\$([0-9a-f]+)$', code.strip())
            if m and table is not None:
                targets.add((table, int(m.group(1), 16)))
        if current and words and words[0] in LENGTH | {'PL_NOP': 0}:
            args = words[1].split(',')
            off = int(args[0].lstrip('$'), 16)
            h, o = seg(size, off)
            length = int(args[1].lstrip('$'), 16) if words[0] == 'PL_NOP' else LENGTH[words[0]]
            sites.append([h, o, o+length, n, line.strip(), current])
        elif not (current and words[:1] and words[0].startswith('PL_')):
            for v in re.findall(r'\$([0-9a-f]{3,5})\b', code):
                literals.append((int(v, 16), n, line.strip()))
    # Hooks hand back to a continuation named in the slave's target tables (c2_*_rest):
    # the native bytes up to it are replaced too.
    for s in sites:
        if s[4].split()[0] == 'PL_P':
            rest = [v for h, v in targets if h == s[0] and s[1] < v <= s[1]+16]
            if rest:
                s[2] = min(rest)
    return sites, literals


def tables(path):
    """E2's and E4's tables for an f1gp file, as the build would make them."""
    import e2_tables, e4_tables
    e2_tables.GAME = Path(path)
    e2_tables.verify = e4_tables.verify = lambda: None
    if not hasattr(e2_tables.Code, 'stock_descend'):
        # F1GP-Ed's startup hook (h0+$1F040) reaches the original entry h0+$88E through
        # its stub's JMP $88E(A2), which the descent cannot follow: seed it.
        e2_tables.Code.stock_descend = e2_tables.Code.descend
        e2_tables.Code.descend = lambda self, seeds: self.stock_descend(
            list(seeds) + ([(0, ENTRY)] if (0, 0) in seeds else []))
    try:
        r = e2_tables.analyse()
        e2 = dict(low=r['low'], high=r['high'], patches=r['patches'], safe=r['safe'], e6=r['e6'],
                  below=r['below'])
    except SystemExit as e:
        e2 = dict(error=str(e))
    try:
        operands, ends = e4_tables.analyse()
        e4 = dict(operands=sorted(operands), ends=sorted(ends))
    except SystemExit as e:
        e4 = dict(error=str(e))
    return e2, e4


def runs(keys):
    out = []
    for h, o in sorted(keys):
        if out and out[-1][0] == h and out[-1][2] == o:
            out[-1][2] = o+1
        else:
            out.append([h, o, o+1])
    return out


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('dirs', nargs='+')
    a.add_argument('--near', type=int, default=32, help='window after each literal (bytes)')
    a.add_argument('--report')
    args = a.parse_args()
    pinned = PINNED.read_bytes()
    layout, size = f1_diff.hunks(pinned), sizes(pinned)
    data, reloc, distinct = writes(args.dirs, pinned, layout)
    written = set(data)
    print(f'{len(distinct)} distinct edited files; {len(written)} bytes and {len(reloc)} relocations written')
    sites, literals = slave(size)
    report = dict(patches=[], names=[], tables=[], relocations=[])

    print('\nPatch sites written by F1GP-Ed:')
    for h, lo, hi, n, text, lst in sites:
        hit = sorted(o for o in range(lo, hi) if (h, o) in written)
        near = min((abs(o-lo) for (hh, o) in written if hh == h), default=None)
        if hit:
            src = sorted(set().union(*(data[(h, o)] for o in hit)))
            print(f'  h{h}+${lo:X}-${hi-1:X} line {n} {text}: {len(hit)} bytes, {len(src)} files, e.g. {src[:4]}')
        report['patches'].append(dict(hunk=h, low=lo, high=hi, line=n, text=text, list=lst,
                                      written=hit, nearest=near))
    print('  nearest written byte to each untouched site: ' + ', '.join(
        f'h{p["hunk"]}+${p["low"]:X} {p["nearest"]}' for p in report['patches']
        if not p['written'] and p['nearest'] is not None and p['nearest'] < 256) or 'none within 256')

    print(f'\nSlave literals whose window [v, v+{args.near}) holds written bytes (review):')
    for v, n, text in literals:
        for h in (0, 2):
            hit = sorted(o for o in range(v, v+args.near) if (h, o) in written)
            if hit:
                src = sorted(set().union(*(data[(h, o)] for o in hit)))
                print(f'  line {n:4} h{h}+${v:X}: written {", ".join(f"+${o-v:X}" for o in hit[:8])}'
                      f' ({len(src)} files)  {text}')
                report['names'].append(dict(line=n, hunk=h, value=v, written=hit, files=len(src), text=text))

    print('\nRelocations changed:')
    for (h, o), src in sorted(reloc.items()):
        print(f'  h{h}+${o:X} ({len(src)} files, e.g. {sorted(src)[:3]})')
        report['relocations'].append(dict(hunk=h, offset=o, files=sorted(src)))

    print('\nE2/E4 tables on each distinct edited file (differences from the stock file\'s):')
    stock2, stock4 = tables(PINNED)
    groups = collections.defaultdict(list)
    for name, path in distinct:
        e2, e4 = tables(path)
        sig = {}
        for k in stock2:
            if e2.get(k) != stock2[k]:
                if isinstance(stock2[k], list) and isinstance(e2.get(k), list):
                    old, now = set(map(tuple, stock2[k]) if k == 'patches' else stock2[k]), \
                        set(map(tuple, e2[k]) if k == 'patches' else e2[k])
                    sig['E2 ' + k] = dict(added=sorted(now - old), removed=sorted(old - now))
                else:
                    sig['E2 ' + k] = e2.get(k, e2.get('error'))
        if e4 != stock4:
            sig['E4'] = e4.get('error') or dict(
                added=sorted(set(e4['operands']) - set(stock4['operands'])),
                removed=sorted(set(stock4['operands']) - set(e4['operands'])))
        groups[json.dumps(sig, sort_keys=True)].append(name)
    for sig, names in sorted(groups.items(), key=lambda g: -len(g[1])):
        print(f'  {len(names)} files (e.g. {names[:3]}): {sig}')
        report['tables'].append(dict(difference=json.loads(sig), files=names))
    if args.report:
        out = Path(args.report).resolve()
        if not out.is_relative_to(ROOT/'tmp'):
            raise ValueError('report must stay in project tmp/')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=1, default=list)+'\n')


if __name__ == '__main__':
    main()
