#!/usr/bin/env python3
"""Entry checks (open-work step 9): 100-field instruction traces of the current source at
both rates (SOL, late type-10, boss, level exit, death on a500-1.5m and a1200-fast), each
checked with patch_entry_trace, indirect_entry_trace and return_entry_trace, plus which
installed patch entries the traces reached. a1200-060 is not traced: its non-cycle-exact
profile has no CPU instruction records.
Usage: tools/entry_traces.py OUT   (OUT under tmp/; OUT/summary.json)"""
import collections, fcntl, json, os, re, subprocess, sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]
os.chdir(root)
sys.path.insert(0, str(root/'tools'))
import _amigaxdev  # noqa: F401
import baseline_checks, rate_matrix, audit_hooks, patch_entry_trace, indirect_entry_trace, return_entry_trace
from amigaxdev import barto

out = Path(sys.argv[1]).resolve()
out.relative_to(root/'tmp')
out.mkdir(parents=True, exist_ok=True)
def scale(tick, n): return (tick*n+11)//12
def trigger(n): return scale(201, n)-1
SCENES = []
for setup in ('a500-1.5m', 'a1200-fast'):
    n = baseline_checks.substeps(setup)
    routes = ('sol', 'type10-late', 'boss')
    for route in routes:
        start, _, flags = rate_matrix.ROUTES[route]
        SCENES.append((f'{setup}-{route}', setup, n, flags, ['--tick', str(scale(start, n))]))
    t = trigger(n)
    SCENES.append((f'{setup}-exit', setup, n, f'-DLEVEL_TEST={t} -DLEVEL_LAST=6', ['--tick', str(t-1)]))
    SCENES.append((f'{setup}-death', setup, n, f'-DDEATH_TEST={t}', ['--tick', str(t-1)]))

def entries(folder, listing, trace):
    meta = {k: int(v, 0) for k, v in re.findall(r'^(code|base)=(\S+)', (folder/'anchor.txt').read_text(), re.M)}
    seen = {pc-meta['code'] for f in trace.fields for pc, _, _ in trace.instructions(f) if pc not in (None, 0x7fffffff)}
    patches = [p for g in audit_hooks.audit(listing)['ranges'] for p in g['patches'] if p['command'] != 'NOP']
    return {f"{p['start']:#x}:{p['command']}": p['start'] in seen for p in patches}

lock = (root/'tmp/rate-matrix.lock').open('a')
print('Waiting for the capture lock', flush=True)
fcntl.flock(lock, fcntl.LOCK_EX)
summary, reached, totals = {}, collections.defaultdict(dict), collections.Counter()
for name, setup, n, flags, window in SCENES:
    folder = baseline_checks.capture(out, name, setup, baseline_checks.base_flags(setup, n)+' '+flags,
                                     window+['--fields', '100'])
    listing = out/(name+'.lst')
    result_path = out/(name+'.json')
    if not result_path.exists():
        trace = barto.load(folder/'trace.bin')
        r = {key: tool.inspect(folder, listing, trace) for key, tool in
             (('all', patch_entry_trace), ('indirect', indirect_entry_trace), ('returns', return_entry_trace))}
        r['entries'] = entries(folder, listing, trace)
        result_path.write_text(json.dumps(r, indent=2)+'\n')
    r = json.loads(result_path.read_text())
    summary[name] = dict(pcs=r['all']['observed_instruction_pcs'], missing=r['all']['missing_pc_records'],
                         indirect=r['indirect']['indirect_executions'], indirect_sites=r['indirect']['source_sites'],
                         returns=r['returns']['observed_returns'], verified=r['returns']['verified_returns'],
                         entered=sum(r['entries'].values()), patches=len(r['entries']))
    totals.update(pcs=r['all']['observed_instruction_pcs'], missing=r['all']['missing_pc_records'],
                  indirect=r['indirect']['indirect_executions'], returns=r['returns']['observed_returns'],
                  verified=r['returns']['verified_returns'], bridged=r['returns']['gap_bridged_returns'])
    for key, hit in r['entries'].items():
        reached['N%d' % n][key] = reached['N%d' % n].get(key, False) or hit
    print(name, summary[name], flush=True)
coverage = {k: dict(entered=sum(v.values()), patches=len(v), never=sorted(x for x, hit in v.items() if not hit)) for k, v in reached.items()}
(out/'summary.json').write_text(json.dumps(dict(scenes=summary, totals=totals, coverage=coverage), indent=2)+'\n')
subprocess.run(['make', '-s', 'slave'], cwd=root, stdout=subprocess.DEVNULL, check=True)
print('DONE traces', json.dumps(coverage), flush=True)
