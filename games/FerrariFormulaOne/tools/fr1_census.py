#!/usr/bin/env python3
"""FR1 census analysis (FASTRAM_PLAN.md FR1) of one fr1_capture.py directory.

  fr1_census.py CAPTURE_DIR            -> CAPTURE_DIR/census.json

Attributes every blit (blitlog) and every CPU Chip data access (memlog) over
the captured B8Draw-to-B8Draw frames:
  - blit sites: the PC of the BLTSIZE write (memlog custom-register write),
    owner routine, channels, minterm, mode, fill, shifts, masks, sizes and the
    regions each channel touches (exact word addresses from the reference
    blitter's address walk);
  - CPU writers and readers by PC and region;
  - DMACONR readers (WaitBlit and any BZERO reader, decided by disassembly);
  - per-frame, per-bank written bytes (persistence).
PCs are reported canonically (native hunks) or as fine:/host: payload labels.
"""
import bisect, collections, json, struct, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path.home() / '.local/share/amiga/pylib'))
import fr0_blits as F

R = Path(__file__).resolve().parents[1]
PLANE = 10320
BANK_BYTES = 3 * PLANE
CUSTOM = {0x040: 'BLTCON0', 0x042: 'BLTCON1', 0x044: 'BLTAFWM', 0x046: 'BLTALWM', 0x048: 'BLTCPTH',
          0x04a: 'BLTCPTL', 0x04c: 'BLTBPTH', 0x04e: 'BLTBPTL', 0x050: 'BLTAPTH', 0x052: 'BLTAPTL',
          0x054: 'BLTDPTH', 0x056: 'BLTDPTL', 0x058: 'BLTSIZE', 0x060: 'BLTCMOD', 0x062: 'BLTBMOD',
          0x064: 'BLTAMOD', 0x066: 'BLTDMOD', 0x070: 'BLTCDAT', 0x072: 'BLTBDAT', 0x074: 'BLTADAT'}


class Pcs:
    """PC -> canonical address and owner label."""

    def __init__(self, cap, res):
        self.sy = res['symbols']; self.hs = res['host_symbols']
        self.probe = int(res['probe'], 16); self.host = int(res['host'], 16)
        self.rows = sorted(json.loads((cap / 'addresses.json').read_text()), key=lambda x: x['actual'])
        self.keys = [x['actual'] for x in self.rows]
        self.labels = sorted((v, k) for k, v in self.sy.items()); self.lk = [v for v, k in self.labels]
        self.hl = sorted((v, k) for k, v in self.hs.items()); self.hk = [v for v, k in self.hl]
        self.entries = native_entries(cap)
        ov = json.loads((R / 'tmp/manifest/step2-overlays.json').read_text())
        self.code_hunks = {h['number'] for g in ov['groups'] for h in g['hunks'] if h['type'] == 'HUNK_CODE'}

    def is_code(self, pc):
        c, h = self.canon(pc)
        return h is not None and h in self.code_hunks

    def canon(self, pc):
        i = bisect.bisect_right(self.keys, pc) - 1
        if i >= 0 and pc < self.rows[i]['actual'] + self.rows[i]['size']:
            return self.rows[i]['old'] + pc - self.rows[i]['actual'], self.rows[i]['hunk']
        return pc, None

    def owner(self, pc):
        if self.probe <= pc < self.probe + max(self.lk) + 0x400:
            v, k = self.labels[bisect.bisect_right(self.lk, pc - self.probe) - 1]
            return f'fine:{k}+{pc - self.probe - v:#x}'
        if self.host <= pc < self.host + max(self.hk):
            v, k = self.hl[bisect.bisect_right(self.hk, pc - self.host) - 1]
            return f'host:{k}+{pc - self.host - v:#x}'
        c, h = self.canon(pc)
        if h is None:
            return f'other:{pc:06x}'
        e = self.entries[bisect.bisect_right(self.entries, c) - 1] if c >= self.entries[0] else 0
        return f'native:${e:05x}+{c - e:#x}'

    def routine(self, pc):
        o = self.owner(pc)
        return o.split('+')[0]


def native_entries(cap):
    """Absolute jsr/jmp targets in the canonical code hunks: routine entries."""
    ov = json.loads((R / 'tmp/manifest/step2-overlays.json').read_text())
    code = [(h['base'], h['size']) for g in ov['groups'] for h in g['hunks'] if h['type'] == 'HUNK_CODE' and h['size']]
    targets = set(b for b, s in code)
    tool = Path.home() / '.local/share/amiga/bin/m68k-amigaos-objdump'
    if not tool.exists():
        from amigaxdev.env import tool as t
        tool = t('objdump')
    for b, s in code:
        out = subprocess.run([str(tool), '-D', '-b', 'binary', '-m', 'm68k:68020', '--adjust-vma=0',
                              f'--start-address={b:#x}', f'--stop-address={b + s:#x}', str(cap / 'canonical.bin')],
                             capture_output=True, text=True).stdout
        for l in out.split('\n'):
            p = l.split('\t')
            if len(p) >= 3 and p[2].strip().startswith(('jsr', 'jmp', 'bsr')):
                arg = p[2].split()[-1]
                if arg.startswith('0x'):
                    try:
                        t2 = int(arg.split(',')[0].split('<')[0], 16)
                    except ValueError:
                        continue
                    if any(cb <= t2 < cb + cs for cb, cs in code):
                        targets.add(t2)
    return sorted(targets)


def walk(b):
    """Exact per-channel word addresses (reads A/B/C, writes D) of one blit."""
    acc = collections.defaultdict(list)
    m = bytearray(F.CHIP + 2)
    rd0, wr0 = F.rd, F.wr
    # Channel attribution in area mode follows pointer order; use a tagged reader.
    con0 = b['con0']; line = b['con1'] & 1
    if line:
        def rd(mm, a):
            acc['C'].append(a & (F.CHIP - 1)); return 0
        def wr(mm, a, v):
            acc['D'].append(a & (F.CHIP - 1))
        F.rd, F.wr = rd, wr
        try:
            F.blit(m, b)
        finally:
            F.rd, F.wr = rd0, wr0
        return acc
    h, v = b['h'] or 64, b['v'] or 1024
    desc = b['con1'] & 2; step = -2 if desc else 2; sgn = -1 if desc else 1
    for ch, bit, mod in (('A', 0x800, 'amod'), ('B', 0x400, 'bmod'), ('C', 0x200, 'cmod'), ('D', 0x100, 'dmod')):
        if con0 & bit:
            p = b[ch.lower() + 'pt']
            for j in range(v):
                for i in range(h):
                    acc[ch].append(p & (F.CHIP - 1)); p += step
                p += sgn * b[mod]
    return acc


def read_mem(raw):
    """Access records (pc, addr, flags); marks have pc 0xffffffff. Stack
    snapshots (pc 0xfffffffe) are returned separately as (pc, sp, longs, at)."""
    mem = []; stacks = []; i = 0
    while i < len(raw):
        r = struct.unpack_from('<3I', raw, i); i += 12
        if r[0] == 0xfffffffe:
            stacks.append((r[1], r[2], struct.unpack_from('<24I', raw, i), len(mem))); i += 96
        else:
            mem.append(r)
    return mem, stacks


def chain(pcs, longs):
    """Plausible return addresses on the stack, as owner labels."""
    out = []
    for v in longs:
        if v & 1 or v < 0x400:
            continue
        o = pcs.owner(v)
        if o.startswith(('fine:', 'host:')) or (o.startswith('native:') and pcs.is_code(v)):
            out.append(o)
        if len(out) >= 6:
            break
    return out


def ranges(addrs, gap=2):
    out = []
    for a in sorted(set(addrs)):
        if out and a <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], a + 2)
        else:
            out.append([a, a + 2])
    return out


def main(cap):
    cap = Path(cap).resolve(); res = json.loads((cap / 'result.json').read_text()); pcs = Pcs(cap, res)
    canon = (cap / 'canonical.bin').read_bytes()
    entry = struct.unpack_from('>H', canon, 0x226ae)[0]
    banks = [struct.unpack_from('>3I', canon, 0x66c92 + 16 * i) for i in range(2)]
    for p in banks:
        assert p[1] - p[0] == PLANE and p[2] - p[1] == PLANE, banks
    bank_lo = [p[0] for p in banks]

    def region(a):
        for i, lo in enumerate(bank_lo):
            if lo <= a < lo + BANK_BYTES:
                return f'bank{i}'
        if 0xdff000 <= a < 0xdff200:
            return 'custom'
        return 'chip'

    blits = F.parse(cap / 'blits.bin')
    raw = (cap / 'mem.bin').read_bytes()
    mem, stacks = read_mem(raw)
    marks = [(i, r[1], r[2]) for i, r in enumerate(mem) if r[0] == 0xffffffff]
    nframes = len(marks) - 1
    frame_of_blit = {}
    for k in range(nframes):
        for bi in range(marks[k][2], marks[k + 1][2]):
            frame_of_blit[bi] = k
    # BLTSIZE writers give the exact issuing instruction per blit, in order.
    size_pcs = [r[0] for r in mem if r[0] != 0xffffffff and r[1] & 0xfffffe == 0xdff058 and r[2] >> 31]
    assert len(size_pcs) == len(blits), (len(size_pcs), len(blits))
    # Custom-register writes per PC (blitter setup sites).
    regw = collections.defaultdict(collections.Counter)
    for pc, a, f in mem:
        if pc != 0xffffffff and f >> 31 and 0xdff040 <= a < 0xdff076:
            regw[pcs.owner(pc)][CUSTOM.get(a & 0x1fe, hex(a))] += 1

    # Caller chains: BLTSIZE snapshots per blit, first-access snapshots per CPU PC.
    size_stacks = [st for st in stacks if any(True for _ in [0]) and mem[st[3] - 1][1] & 0xfffffe == 0xdff058 and mem[st[3] - 1][2] >> 31 and mem[st[3] - 1][0] == st[0]]
    assert len(size_stacks) == len(blits), (len(size_stacks), len(blits))
    callers = collections.defaultdict(collections.Counter)
    for st in size_stacks:
        callers[pcs.owner(st[0])][' < '.join(chain(pcs, st[2]))] += 1
    cpu_callers = {pcs.owner(st[0]): ' < '.join(chain(pcs, st[2])) for st in stacks if not (mem[st[3] - 1][1] & 0xfffffe == 0xdff058 and mem[st[3] - 1][2] >> 31)}
    # Blit sites.
    bank_ev = collections.Counter(); bank_rev = collections.Counter()
    sites = collections.OrderedDict(); bank_written = [[bytearray(BANK_BYTES) for _ in banks] for _ in range(nframes)]
    src = collections.defaultdict(lambda: collections.defaultdict(set))   # chip range -> reader -> channels
    chip_blit_reads = collections.defaultdict(list); chip_blit_writes = collections.defaultdict(list)
    for b, spc in zip(blits, size_pcs):
        acc = walk(b); fr = frame_of_blit.get(b['index'], -1)
        key = pcs.owner(spc)
        s = sites.setdefault(key, dict(site=key, routine=pcs.routine(spc), pc_canonical=hex(pcs.canon(spc)[0]), count=0,
                                       per_frame=collections.Counter(), kinds=collections.Counter(), minterms=collections.Counter(),
                                       ash=set(), bsh=set(), afwm=set(), alwm=set(), sizes=collections.Counter(),
                                       fill=collections.Counter(), dest=collections.Counter(), reads=collections.Counter(),
                                       words=0))
        s['count'] += 1; s['per_frame'][fr] += 1; s['kinds'][F.kind(b)] += 1; s['minterms'][f"{b['con0'] & 255:02x}"] += 1
        s['ash'].add(b['con0'] >> 12); s['bsh'].add(b['con1'] >> 12); s['afwm'].add(f"{b['afwm']:04x}"); s['alwm'].add(f"{b['alwm']:04x}")
        s['sizes'][f"{b['h'] or 64}x{b['v'] or 1024}" if not b['con1'] & 1 else f"line{b['v'] or 1024}"] += 1
        s['fill'][('ife' if b['con1'] & 8 else 'efe' if b['con1'] & 0x10 else 'none') + ('+fci' if b['con1'] & 4 else '')] += 1
        for ch, addrs in acc.items():
            s['words'] += len(addrs) if ch == 'D' else 0
            regs = collections.Counter(region(a) for a in addrs)
            for rg, n in regs.items():
                (s['dest'] if ch == 'D' else s['reads'])[f'{ch}:{rg}'] += n
            for a in addrs:
                rg = region(a)
                if rg.startswith('bank') and ch == 'D' and fr >= 0:
                    i = int(rg[4]); o = a - bank_lo[i]; bank_written[fr][i][o] = bank_written[fr][i][o + 1] = 1
                    bank_ev[(key, fr, i)] += 2
                if rg.startswith('bank') and ch != 'D' and fr >= 0:
                    bank_rev[(key + '|' + ch, fr, int(rg[4]))] += 2
            if ch == 'D':
                chip_blit_writes[key] += [a for a in addrs if region(a) == 'chip']
            else:
                chip_blit_reads[(key, ch)] += [a for a in addrs if region(a) == 'chip']

    # CPU accesses.
    cpu = collections.OrderedDict(); dmaconr = collections.Counter(); cpu_chip = collections.defaultdict(list)
    cur = -1
    for pc, a, f in mem:
        if pc == 0xffffffff:
            cur = a; continue
        rg = region(a); w = f >> 31; sz = f >> 24 & 7
        if a == 0xdff002 and not w:
            dmaconr[pc] += 1; continue
        if rg == 'custom':
            continue
        key = (pcs.owner(pc), 'W' if w else 'R', rg)
        c = cpu.setdefault(key, dict(pc=key[0], routine=pcs.routine(pc), rw=key[1], region=rg, count=0, sizes=collections.Counter(), addrs=[]))
        c['count'] += 1; c['sizes'][sz] += 1; c['addrs'].append(a)
        if rg.startswith('bank') and 0 <= cur < nframes:
            (bank_ev if w else bank_rev)[(key[0] + ('' if w else '|cpu'), cur, int(rg[4]))] += sz
        if rg.startswith('bank') and w and 0 <= cur < nframes:
            i = int(rg[4]); o = a - bank_lo[i]
            for k in range(sz):
                if 0 <= o + k < BANK_BYTES:
                    bank_written[cur][i][o + k] = 1
        if rg == 'chip':
            cpu_chip[(key[0], key[1])] += list(range(a, a + sz))

    # DMACONR readers: classify the reading instruction (btst #14 = WaitBlit; bit 13 = BZERO).
    fastb = (cap / 'frame-start-fast.bin').read_bytes(); chipb = (cap / 'frame-start.bin').read_bytes()
    from amigaxdev.env import tool
    def dis(pc, n=0x10):
        dump, base = (cap / 'frame-start-fast.bin', 0x200000) if pc >= 0x200000 else (cap / 'frame-start.bin', 0)
        out = subprocess.run([tool('objdump'), '-D', '-b', 'binary', '-m', 'm68k:68020', f'--adjust-vma={base:#x}',
                              f'--start-address={pc:#x}', f'--stop-address={pc + n:#x}', str(dump)],
                             capture_output=True, text=True).stdout
        return [l.split('\t')[-1].strip() for l in out.split('\n') if l.startswith(' ') and '\t' in l]
    dmac = []
    for pc, n in dmaconr.most_common():
        d = dis(pc, 0x0c)
        text = ' ; '.join(d[:2])
        bzero = ('#13' in text or '0x2000' in text or '#8192' in text) and 'btst' in text or ('and' in text and '0x2000' in text)
        dmac.append(dict(pc=pcs.owner(pc), pc_canonical=hex(pcs.canon(pc)[0]), reads=n, insn=text, bzero_reader=bool(bzero)))

    # Persistence: bank bytes written in each frame (per bank drawn that frame).
    drawn = []
    for k in range(nframes):
        drawn.append([sum(bank_written[k][i]) for i in range(2)])
    back = [0 if d[0] > d[1] else 1 for d in drawn]
    def split(ev):
        o = collections.defaultdict(lambda: dict(back=0, front=0))
        for (k, fr, i), n in ev.items():
            o[k]['back' if i == back[fr] else 'front'] += n
        return {k: v for k, v in sorted(o.items())}
    bank_split = dict(writes=split(bank_ev), reads=split(bank_rev), back_bank_per_frame=back)
    pers = {}
    for i in range(2):
        fs = [k for k in range(nframes) if drawn[k][i] > 1000]
        if not fs:
            continue
        rows_any = collections.Counter(); rows_all = collections.Counter()
        union = bytearray(BANK_BYTES); inter = bytearray(b'\1' * BANK_BYTES)
        for k in fs:
            for o in range(BANK_BYTES):
                union[o] |= bank_written[k][i][o]; inter[o] &= bank_written[k][i][o]
        def rows(buf):
            out = []
            for pl in range(3):
                for r in range(215):
                    seg = buf[pl * PLANE + r * 48: pl * PLANE + r * 48 + 48]
                    out.append(sum(seg))
            return out
        u = rows(union); n = rows(inter)
        untouched = [r for r in range(215) if all(u[pl * 215 + r] == 0 for pl in range(3))]
        partial = [r for r in range(215) if 0 < min(n[pl * 215 + r] for pl in range(3)) < 48 or any(0 < n[pl * 215 + r] < 48 for pl in range(3))]
        full = [r for r in range(215) if all(n[pl * 215 + r] == 48 for pl in range(3))]
        vis_never = []; vis_some = 0; vis_total = 0
        for pl in range(3):
            for r in range(200):
                run = None
                for c in range(4, 44):
                    o = pl * PLANE + r * 48 + c; vis_total += 1
                    if union[o] and not inter[o]:
                        vis_some += 1
                    if not union[o]:
                        if run and run[2] == c - 1:
                            run[2] = c
                        else:
                            run = [pl, r, c, c]; run[2] = c; vis_never.append(run)
        vis_never = [[pl, r, c0, c1] for pl, r, c0, c1 in [(x[0], x[1], x[3], x[2]) for x in vis_never]]
        pers_vis = dict(visible_bytes=vis_total, visible_never_written=sum(c1 - c0 + 1 for pl, r, c0, c1 in vis_never),
                        visible_written_some_frames=vis_some,
                        visible_never_runs=[f'p{pl} r{r} b{c0}-{c1}' for pl, r, c0, c1 in vis_never][:400])
        pers[f'bank{i}'] = dict(frames=fs, **pers_vis, bytes_written_each_frame=sum(inter), bytes_written_any_frame=sum(union),
                                rows_never_written=compress(untouched), rows_fully_written_every_frame=compress(full),
                                rows_partly_written=compress(partial))

    def rng(addrs):
        return [[hex(a), hex(e)] for a, e in ranges(addrs, 64)]
    out = dict(capture=str(cap.relative_to(R)), frames=nframes, scene=res.get('scope'), slave_sha256=res['slave_sha256'],
               banks=[[hex(x) for x in p] for p in banks], back_entry=hex(entry),
               blits=len(blits), blits_per_frame=[marks[k + 1][2] - marks[k][2] for k in range(nframes)],
               bank_bytes_written_per_frame=drawn,
               blit_sites=[], cpu=[], dmaconr=dmac, blitter_register_writers={k: dict(v) for k, v in regw.items()},
               chip_sources_blit={f'{k}|{ch}': rng(v) for (k, ch), v in chip_blit_reads.items() if v},
               chip_dest_blit={k: rng(v) for k, v in chip_blit_writes.items() if v},
               chip_cpu={f'{k}|{rw}': rng(v) for (k, rw), v in cpu_chip.items()}, persistence=pers, bank_split=bank_split)
    for s in sites.values():
        s = dict(s); s['per_frame'] = [s['per_frame'][k] for k in range(nframes)]
        for k in ('ash', 'bsh', 'afwm', 'alwm'):
            s[k] = sorted(s[k])
        for k in ('kinds', 'minterms', 'sizes', 'fill', 'dest', 'reads'):
            s[k] = dict(s[k].most_common(12))
        s['callers'] = dict(callers[s['site']].most_common(8))
        out['blit_sites'].append(s)
    for c in cpu.values():
        c = dict(c); a = c.pop('addrs'); c['sizes'] = dict(c['sizes'])
        c['ranges'] = rng(a)[:12]; c['range_count'] = len(ranges(a, 64)); c['caller'] = cpu_callers.get(c['pc'], ''); out['cpu'].append(c)
    (cap / 'census.json').write_text(json.dumps(out, indent=1) + '\n')
    return out


def compress(rows):
    out = []
    for r in rows:
        if out and r == out[-1][1] + 1:
            out[-1][1] = r
        else:
            out.append([r, r])
    return [f'{a}-{b}' if a != b else str(a) for a, b in out]


if __name__ == '__main__':
    o = main(sys.argv[1])
    print('frames', o['frames'], 'blits/frame', o['blits_per_frame'], 'bank bytes', o['bank_bytes_written_per_frame'])
    print('sites', len(o['blit_sites']), 'cpu keys', len(o['cpu']), 'dmaconr', [(d['pc'], d['reads'], d['insn'], d['bzero_reader']) for d in o['dmaconr']])
