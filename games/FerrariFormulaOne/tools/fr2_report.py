#!/usr/bin/env python3
"""FR2: merge oracle runs and case statistics into manifest/fr2-oracle.json.

  fr2_report.py PROFILE [PROFILE...]
"""
import collections, hashlib, json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fr2_cases import REC, FRB, xorshift_fill, run_model
from fr2_model import Mem

R = Path(__file__).resolve().parents[1]


def case_stats():
    blob = (R / 'tmp/build/fr2-data/FR2Cases.bin').read_bytes()
    meta = json.loads((R / 'tmp/build/fr2-data/cases.json').read_text())
    by = collections.Counter(); words = 0; changed = 0; minterms = set(); lines = collections.Counter()
    for i in range(len(blob) // REC):
        rec = blob[i * REC:(i + 1) * REC]
        size2, reloc, seed, ln, pattern, kind = struct.unpack_from('>HHIIHH', rec, 0x3c)
        g = lambda o: struct.unpack_from('>H', rec, o)[0]
        regs = {k: (struct.unpack_from('>I', rec, o)[0] if k in ('cpt', 'bpt', 'apt', 'dpt') else g(o)) for k, o in FRB.items()}
        d = xorshift_fill(ln, seed, pattern); m = bytearray(d)
        run_model(regs, regs['size'], size2, Mem(m))
        w = sum(1 for j in range(0, ln, 2) if m[j:j + 2] != d[j:j + 2]); words += w; changed += w > 0
        c0, c1 = regs['con0'], regs['con1']
        k = 'line' if c1 & 1 else ''.join(c for c, b in zip('ABCD', (0x800, 0x400, 0x200, 0x100)) if c0 & b) + \
            ('-fill' if c1 & 0x18 else '') + ('-desc' if c1 & 2 else '')
        by[('captured' if kind == 0 else 'generated', k)] += 1
        minterms.add(c0 & 255)
        if c1 & 1:
            lines[(c1 >> 2 & 7, bool(c1 & 2))] += 1
    return dict(records=len(blob) // REC, captured_unique=meta['captured_unique'], captured_per_scene=meta['captured_per_scene'],
                generated=meta['generated'], cases_with_changed_words=changed, changed_words=words,
                minterms_covered=len(minterms), line_octants_sing={f'octant{o}{"-sing" if s else ""}': n for (o, s), n in sorted(lines.items())},
                by_class={f'{a}:{b}': n for (a, b), n in sorted(by.items())},
                cases_sha256=hashlib.sha256(blob).hexdigest())


def main(profiles):
    runs = {p: json.loads((R / f'tmp/step5/fr2-oracle-{p}/result.json').read_text()) for p in profiles}
    out = dict(scope='FR2 oracle (FASTRAM_PLAN.md FR2): hardware blitter in Chip vs FastRenderBlit in Fast, '
                     'emulator cycle-exact blitter as oracle; zero-difference gate.',
               cases=case_stats(),
               runs={p: {k: v for k, v in r.items() if k != 'mismatches'} | {'mismatches_first': r.get('mismatches', [])[:20]}
                     for p, r in runs.items()},
               gate='passed' if all(r.get('status') == 'passed' for r in runs.values()) else 'failed')
    (R / 'tmp/manifest/fr2-oracle.json').write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k != 'cases'} | {'cases': {k: out['cases'][k] for k in ('records', 'changed_words', 'minterms_covered')}}, indent=1))
    return out


if __name__ == '__main__':
    main(sys.argv[1:])
