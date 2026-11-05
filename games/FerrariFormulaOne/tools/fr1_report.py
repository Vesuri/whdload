#!/usr/bin/env python3
"""FR1: merge per-scene census.json files into manifest/fr1-census.json.

  fr1_report.py SCENE=CAPTURE_DIR [SCENE=CAPTURE_DIR...]
"""
import collections, json, struct, sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]


def merge_ranges(rs, gap=64):
    out = []
    for a, e in sorted(rs):
        if out and a <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([a, e])
    return out


def copper(cap, banks):
    """Display geometry from the copper lists that load each bank's plane pointers."""
    m = (cap / 'frame-start.bin').read_bytes(); lists = []
    for a in range(0, 0x80000, 2):
        if m[a:a + 2] == b'\x00\xe0' and m[a + 4:a + 6] == b'\x00\xe2':
            p = struct.unpack_from('>H', m, a + 2)[0] << 16 | struct.unpack_from('>H', m, a + 6)[0]
            for i, b in enumerate(banks):
                if b <= p < b + 64:
                    st = a
                    while st > 0 and struct.unpack_from('>H', m, st - 4)[0] != 0xffff and m[st - 4:st - 2] not in (b'\x2b\x01',):
                        st -= 4
                    regs = {}
                    x = a - 0x50
                    while x < a + 0x40:
                        r, v = struct.unpack_from('>HH', m, x); x += 4
                        if r == 0xffff:
                            break
                        if not r & 1:
                            regs.setdefault(r, v)
                        else:
                            regs.setdefault(f'wait{len([k for k in regs if str(k).startswith("wait")])}', f'{r:04x}{v:04x}')
                    lists.append(dict(bank=i, copper_bplpt_at=hex(a), plane0=hex(p), offset=p - b,
                                      regs={(f'{k:03x}' if isinstance(k, int) else k): (f'{v:04x}' if isinstance(v, int) else v) for k, v in regs.items()}))
    return lists


def main(args):
    scenes = {}
    for a in args:
        k, p = a.split('=', 1); scenes[k] = (R / p if not Path(p).is_absolute() else Path(p))
    cs = {k: json.loads((p / 'census.json').read_text()) for k, p in scenes.items()}
    first = next(iter(cs.values()))
    banks = [int(b[0], 16) for b in first['banks']]
    for k, c in cs.items():
        assert [int(b[0], 16) for b in c['banks']] == banks, k
    sites = collections.OrderedDict()
    for sc, c in cs.items():
        for s in c['blit_sites']:
            m = sites.setdefault(s['site'], dict(site=s['site'], routine=s['routine'], pc_canonical=s['pc_canonical'],
                                                 scenes={}, kinds=collections.Counter(), minterms=collections.Counter(),
                                                 ash=set(), bsh=set(), afwm=set(), alwm=set(), sizes=collections.Counter(),
                                                 fill=collections.Counter(), dest=collections.Counter(), reads=collections.Counter(),
                                                 callers=collections.Counter()))
            m['scenes'][sc] = dict(per_frame=s['per_frame'], words_written=s['words'] // max(1, c['frames']))
            for f in ('kinds', 'minterms', 'sizes', 'fill', 'dest', 'reads', 'callers'):
                m[f].update(s[f])
            for f in ('ash', 'bsh', 'afwm', 'alwm'):
                m[f].update(s[f])
    site_list = []
    for m in sites.values():
        m = dict(m)
        for f in ('ash', 'bsh', 'afwm', 'alwm'):
            m[f] = sorted(m[f])
        for f in ('kinds', 'minterms', 'sizes', 'fill', 'dest', 'reads'):
            m[f] = dict(m[f].most_common(16))
        m['callers'] = [k for k, n in m['callers'].most_common(24)]
        site_list.append(m)
    cpu = collections.OrderedDict()
    for sc, c in cs.items():
        for x in c['cpu']:
            if not x['region'].startswith('bank'):
                continue
            k = (x['pc'], x['rw'])
            m = cpu.setdefault(k, dict(pc=x['pc'], routine=x['routine'], rw=x['rw'], scenes={}, sizes=collections.Counter(), caller=x['caller']))
            m['scenes'].setdefault(sc, 0); m['scenes'][sc] += x['count'] // max(1, c['frames'])
            m['sizes'].update({int(a): b for a, b in x['sizes'].items()})
    cpu_list = []
    for m in cpu.values():
        m = dict(m); m['sizes'] = dict(m['sizes']); m['accesses_per_frame'] = m.pop('scenes'); cpu_list.append(m)
    # Front-bank access (bank on display while the other is drawn).
    front = collections.defaultdict(dict)
    for sc, c in cs.items():
        for kind in ('writes', 'reads'):
            for who, v in c['bank_split'][kind].items():
                if v['front']:
                    front[f'{kind[:-1]} {who}'][sc] = v['front'] // max(1, c['frames'])
    # Non-bank Chip sources read by blits, destinations written by blits.
    srcs = collections.defaultdict(lambda: dict(readers=set(), scenes=set()))
    raw = collections.defaultdict(list)
    for sc, c in cs.items():
        for key, rs in c['chip_sources_blit'].items():
            for a, e in rs:
                raw['blit-read'].append((int(a, 16), int(e, 16), key, sc))
        for key, rs in c['chip_dest_blit'].items():
            for a, e in rs:
                raw['blit-write'].append((int(a, 16), int(e, 16), key, sc))
        for key, rs in c['chip_cpu'].items():
            who, rw = key.rsplit('|', 1)
            for a, e in rs:
                raw['cpu-' + ('write' if rw == 'W' else 'read')].append((int(a, 16), int(e, 16), who, sc))
    allr = merge_ranges([(a, e) for v in raw.values() for a, e, w, s in v], 256)
    chip = []
    for a, e in allr:
        ent = dict(range=[hex(a), hex(e)], bytes=e - a)
        for kind, v in raw.items():
            who = collections.defaultdict(set)
            for x, y, w, s in v:
                if x < e and y > a:
                    who[w].add(s)
            if who:
                ent[kind] = {w: sorted(s) for w, s in sorted(who.items())}
        chip.append(ent)
    pers = {sc: c['persistence'] for sc, c in cs.items()}
    out = dict(scope='FR1 census (FASTRAM_PLAN.md FR1): 030-50 BCE emulator captures; blitlog + memlog.',
               scenes={sc: dict(capture=c['capture'], frames=c['frames'], blits_per_frame=c['blits_per_frame'],
                                bank_bytes_written_per_frame=c['bank_bytes_written_per_frame'], slave_sha256=c['slave_sha256'])
                       for sc, c in cs.items()},
               banks=first['banks'], plane_stride=10320, rows_allocated=215,
               display=copper(next(iter(scenes.values())), banks),
               blit_sites=site_list, cpu_bank_access=cpu_list, front_bank_access=dict(front),
               dmaconr_readers=sorted({(d['pc'], d['insn'], d['bzero_reader']) for c in cs.values() for d in c['dmaconr']}),
               chip_outside_banks=chip, persistence=pers)
    (R / 'tmp/manifest/fr1-census.json').write_text(json.dumps(out, indent=1, default=list) + '\n')
    return out


if __name__ == '__main__':
    o = main(sys.argv[1:])
    print('sites', len(o['blit_sites']), 'cpu bank keys', len(o['cpu_bank_access']), 'chip ranges', len(o['chip_outside_banks']))
