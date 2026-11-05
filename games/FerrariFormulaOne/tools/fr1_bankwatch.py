#!/usr/bin/env python3
"""FR1 persistence: summarize an FF1_BANKWATCH log from a lifecycle route.

  fr1_bankwatch.py LOG RUN_DIR [OUT.json]

LOG lines: "v FIELD" then "K PC LO HI COUNT" (K: W/R CPU write/read,
D/S blit destination/source span). RUN_DIR is the harness output directory with
result.json (probe, host, table, symbols) and a memory dump used to map PCs.
Fields are grouped into runs of consecutive fields with the same writer set;
each writer is labelled with its owner (fine:/host:/native:/other:).
"""
import bisect, collections, json, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def load(log):
    fields = collections.OrderedDict(); cur = None
    for line in Path(log).read_text().split('\n'):
        p = line.split()
        if not p:
            continue
        if p[0] == 'v':
            cur = int(p[1]); fields.setdefault(cur, [])
        else:
            fields[cur].append((p[0], int(p[1], 16), int(p[2], 16), int(p[3], 16), int(p[4])))
    return fields


class Owner:
    def __init__(self, run):
        res = json.loads((run / 'result.json').read_text())
        self.probe = int(res['probe'], 16) if 'probe' in res else 0
        sy = res.get('symbols', {}); hs = res.get('host_symbols', {})
        if not sy and 'launch' in res:
            build = json.loads((Path(res['launch']['SLAVE']).parent / 'build.json').read_text())
            hs = build['host_symbols']; sy = build['payloads'][res.get('kind', 'fine')]['symbols']
        self.host = int(res['host'], 16) if 'host' in res else (int(res['marker'], 16) - hs['FF1PublicMarker'] if hs else 0)
        self.lab = sorted((v, k) for k, v in sy.items()); self.lk = [v for v, k in self.lab]
        self.hl = sorted((v, k) for k, v in hs.items()); self.hk = [v for v, k in self.hl]
        self.rows = []
        mem = None
        for n in ('takeover', 'start', 'memory'):
            if (run / f'{n}.bin').exists():
                mem = bytearray((run / f'{n}.bin').read_bytes())
                if (run / f'{n}-fast.bin').exists():
                    mem += bytes(0x200000 - len(mem)) + (run / f'{n}-fast.bin').read_bytes()
                break
        if mem is not None and 'table' in res:
            from step5_b7_addresses import Addresses
            try:
                self.rows = sorted(Addresses(mem, int(res['table'], 16)).rows, key=lambda x: x['actual'])
            except AssertionError:
                self.rows = []
        self.keys = [x['actual'] for x in self.rows]

    def __call__(self, pc):
        if self.lk and self.probe <= pc < self.probe + max(self.lk) + 0x400:
            v, k = self.lab[bisect.bisect_right(self.lk, pc - self.probe) - 1]; return f'fine:{k}'
        if self.hk and self.host <= pc < self.host + max(self.hk):
            v, k = self.hl[bisect.bisect_right(self.hk, pc - self.host) - 1]; return f'host:{k}'
        i = bisect.bisect_right(self.keys, pc) - 1
        if i >= 0 and pc < self.rows[i]['actual'] + self.rows[i]['size']:
            return f"native:{self.rows[i]['old'] + pc - self.rows[i]['actual']:05x}"
        return f'other:{pc:06x}'


def main(log, run, out=None):
    fields = load(log); own = Owner(Path(run))
    runs = []
    for v, ents in fields.items():
        sig = tuple(sorted({(k, own(pc)) for k, pc, lo, hi, n in ents}))
        if runs and runs[-1]['sig'] == sig and v - runs[-1]['last'] <= 2:
            r = runs[-1]; r['last'] = v; r['fields'] += 1
        else:
            r = dict(first=v, last=v, fields=1, sig=sig, span=collections.defaultdict(lambda: [1 << 32, 0, 0]))
            runs.append(r)
        for k, pc, lo, hi, n in ents:
            s = r['span'][(k, own(pc))]; s[0] = min(s[0], lo); s[1] = max(s[1], hi); s[2] += n
    res = []
    for r in runs:
        res.append(dict(fields=[r['first'], r['last']], count=r['fields'],
                        writers={f'{k} {o}': [hex(a), hex(b), n] for (k, o), (a, b, n) in sorted(r['span'].items())}))
    tot = collections.Counter()
    for v, ents in fields.items():
        for k, pc, lo, hi, n in ents:
            tot[(k, own(pc))] += 1
    summary = dict(log=str(log), fields_with_bank_access=len(fields), runs=len(res),
                   owners={f'{k} {o}': n for (k, o), n in sorted(tot.items())}, timeline=res)
    if out:
        Path(out).write_text(json.dumps(summary, indent=1) + '\n')
    return summary


if __name__ == '__main__':
    s = main(*sys.argv[1:4])
    print('fields', s['fields_with_bank_access'], 'runs', s['runs'])
    for k, n in s['owners'].items():
        print(f'{n:6d} fields  {k}')
