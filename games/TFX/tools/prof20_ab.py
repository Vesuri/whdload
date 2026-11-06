#!/usr/bin/env python3
"""A/B report for two 2,000-field strict profiles: emulator throughput plus estimated 040 cost.

  prof20_ab.py CONTROL_DIR CONTROL_LISTING CANDIDATE_DIR CANDIDATE_LISTING [OUT.json]

Checks that both runs use the same emulator, seed, tape and window, then reports
publications, interval histograms, emulator and estimated-040 cycles per frame, FPSP
entries and the largest per-region changes. Acceptance (plan rules): estimated 040
cost must fall; emulator publications must not fall unless explained by FPU bias.
"""
import collections, json, sys, csv
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import prof20_cost040 as C


def load(d, lst):
    d = Path(d)
    m = json.loads((d / 'manifest.json').read_text()); c = json.loads((d / 'counts.json').read_text())
    pubs = [e['vblank'] for e in c['events'] if e['kind'] == 'publish' and c['window'][0] <= e['vblank'] < c['window'][1]]
    ctx, est, agg = C.estimate(d, lst)
    fpsp = sum(int(r[5]) for r in csv.reader((d / 'profile.csv').open()) if r[0] == 'exception' and int(r[2]) == 11)
    entry = json.loads((d / 'entry-match.json').read_text()) if (d / 'entry-match.json').exists() else None
    return dict(dir=str(d), manifest=m, publications=c['publications'], fps=c['pal50_equivalent_fps'], window=c['window'],
                intervals=dict(sorted(collections.Counter(b - a for a, b in zip(pubs, pubs[1:])).items())),
                emu_cpf=ctx.duration / ctx.div / ctx.frames, est_cpf=est / ctx.frames, fpsp=fpsp, entry_match=entry,
                regions={k: dict(est=v[0] / ctx.frames, emu=v[1] / ctx.div / ctx.frames) for k, v in agg.items()})


def main():
    a = load(sys.argv[1], sys.argv[2]); b = load(sys.argv[3], sys.argv[4])
    same = {k: a['manifest'].get(k) == b['manifest'].get(k) for k in ('emulator_sha256', 'tape_sha256', 'seed_sha256', 'executable_sha256', 'fpsp040_sha256')}
    same['window'] = a['window'] == b['window']
    print('same inputs:', same)
    for n, r in (('control', a), ('candidate', b)):
        print(f"{n:9} pubs {r['publications']:4} fps {r['fps']:6.3f} emu {r['emu_cpf']:11,.0f} est {r['est_cpf']:11,.0f} cyc/frame"
              f"  fpsp {r['fpsp']}  intervals {r['intervals']}  entry {r['entry_match']}")
    # Per-frame totals change with cadence; compare per-frame region costs.
    d_emu = 100 * (b['emu_cpf'] / a['emu_cpf'] - 1); d_est = 100 * (b['est_cpf'] / a['est_cpf'] - 1)
    print(f"publications {b['publications'] - a['publications']:+d} ({100 * (b['publications'] / a['publications'] - 1):+.2f}%)"
          f"  emu cycles/frame {d_emu:+.2f}%  est-040 cycles/frame {d_est:+.2f}%")
    keys = set(a['regions']) | set(b['regions'])
    z = dict(est=0, emu=0)
    diff = sorted(((b['regions'].get(k, z)['est'] - a['regions'].get(k, z)['est'], b['regions'].get(k, z)['emu'] - a['regions'].get(k, z)['emu'], k) for k in keys), key=lambda x: abs(x[0]), reverse=True)
    print('largest per-frame region changes (est-040 cycles, emulator cycles):')
    for de, du, k in diff[:12]:
        print(f"  {de:+10,.0f} {du:+10,.0f}  {k}")
    verdict = dict(inputs_match=all(same.values()), est_falls=b['est_cpf'] < a['est_cpf'], emu_not_worse=b['publications'] >= a['publications'])
    print('verdict:', verdict)
    if len(sys.argv) > 5:
        for r in (a, b): r.pop('manifest')
        Path(sys.argv[5]).write_text(json.dumps(dict(same=same, control=a, candidate=b, verdict=verdict,
                                                     changes=[dict(region=k, est=de, emu=du) for de, du, k in diff[:40]]), indent=1))


if __name__ == '__main__':
    main()
