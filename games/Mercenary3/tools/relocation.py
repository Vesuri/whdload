"""Where the performance slave copies game code in its expansion memory (M1, S3, F2, F5).

Maps a copied instruction's address back to the original chip address, given the
allocated ws_ExpMem base (route_profile.py records it in route.json). The S3/F2 ranges come
from src/renderer-relocs.i and renderer-f2.i; the M1 blocks and area offsets follow _hotcode and
_hotrenderer in src/Mercenary3.slave.asm. Copies keep the original instruction
lengths, so opcodes and offsets within a block match the chip original. With F5 (Custom1
bit 20) the blocks are translated instead (src/translate-f5.i): instructions may grow,
and addresses map through each block's growth list. Map(expmem) takes F5 from WHD_ARGS
(CUSTOM1 bit 20, or the release default when CUSTOM5 is not 0); f5= overrides.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISK_DELTA = 0x3cb0


def _constants():
    text = open(os.path.join(ROOT, 'src/Mercenary3.slave.asm'), encoding='latin1').read()
    return {k: int(v, 16) for k, v in re.findall(r'^(\w+)\s*=\s*\$([0-9a-fA-F]+)', text, re.M)}


def blocks(expmem):
    """(copy start, copy end, chip start) for each copied block."""
    k = _constants()
    hot = expmem + k['STACKSIZE']
    # M1: Disk.1 $4EDE4..$4EF92, then $5B030..$5B918, back to back.
    m1 = [(0x4b134, 0x4b2e2), (0x57380, 0x57c68)]
    out = []
    for lo, hi in m1:
        out.append((hot, hot + hi - lo, lo))
        hot += hi - lo
    render = expmem + k['STACKSIZE'] + k['HOTSIZE'] + k['TABLEMEM'] + k['RESTOREMEM']
    seen = set()
    for filename, label in (('renderer-relocs.i', '_render_ranges'),
                            ('renderer-f2.i', '_f2_ranges')):
        text = open(os.path.join(ROOT, 'src', filename), encoding='latin1').read()
        text = text.split(label, 1)[1].split('dc.l\t0', 1)[0]
        for lo, hi, off in re.findall(r'dc\.l\s+\$(\w+)-\$3cb0,\$(\w+)-\$3cb0,\$(\w+)', text):
            lo, hi = int(lo, 16) - DISK_DELTA, int(hi, 16) - DISK_DELTA
            entry = (render + int(off, 16), render + int(off, 16) + hi - lo, lo)
            if entry not in seen:
                out.append(entry)
                seen.add(entry)
    return out


def islands(expmem):
    """{island address: chip target} for the renderer's JMP islands (external word branches)."""
    k = _constants()
    render = expmem + k['STACKSIZE'] + k['HOTSIZE'] + k['TABLEMEM'] + k['RESTOREMEM']
    out = {}
    for filename, label in (('renderer-relocs.i', '_render_branches'),
                            ('renderer-f2.i', '_f2_branches')):
        text = open(os.path.join(ROOT, 'src', filename), encoding='latin1').read()
        text = text.split(label, 1)[1].split('dc.l\t0', 1)[0]
        for target, off in re.findall(r'dc\.l\s+\$\w+-\$3cb0,\$(\w+)-\$3cb0,\$(\w+)', text):
            out[render + int(off, 16)] = int(target, 16) - DISK_DELTA
    return out


def f5_enabled(whd_args=None):
    text = os.environ.get('WHD_ARGS', '') if whd_args is None else whd_args
    args = dict(a.split('=', 1) for a in text.split() if '=' in a)
    if 'CUSTOM1' in args and args.get('CUSTOM5') == '0':
        return bool(int(args['CUSTOM1'], 0) & (1 << 20))
    return args.get('CUSTOM5', '1') != '0'


def f5_layout(expmem):
    """[(lo, hi, copy start, [(offset, growth)])] and {island: target}, from translate-f5.i."""
    k = _constants()
    hot = k['STACKSIZE']
    render = k['STACKSIZE'] + k['HOTSIZE'] + k['TABLEMEM'] + k['RESTOREMEM']
    text = open(os.path.join(ROOT, 'src/translate-f5.i'), encoding='latin1').read()
    base = {'F5HOT': hot, 'F5RENDER': render}
    out = []
    for lo, hi, dest, off, label in re.findall(
            r'dc\.l\t\$(\w+)-\$3cb0,\$(\w+)-\$3cb0,(F5\w+)\+\$(\w+),_f5_r\d+-_f5_blocks,(_f5_t\d+)-', text):
        th = text.split('\n' + label + '\n', 1)[1]
        words = re.findall(r'\$?([0-9a-f]+)', ' '.join(
            line.split('dc.w', 1)[1] for line in th.split('\n') if 'dc.w' in line and not line.startswith('_')).split('$ffff')[0])
        vals = [int(w, 16) if i % 2 == 0 else int(w) for i, w in enumerate(words)]
        out.append((int(lo, 16) - DISK_DELTA, int(hi, 16) - DISK_DELTA,
                    expmem + base[dest] + int(off, 16), list(zip(vals[0::2], vals[1::2]))))
    isl = {}
    for target, dest, off in re.findall(r'dc\.l\t\$\w+-\$3cb0,\$(\w+)-\$3cb0,(F5\w+)\+\$(\w+)\n',
                                        text.split('_f5_branches', 1)[1].split('dc.l\t0', 1)[0] + '\n'):
        isl[expmem + base[dest] + int(off, 16)] = int(target, 16) - DISK_DELTA
    return out, isl


class Map:
    def __init__(self, expmem, f5=None):
        self.f5 = bool(expmem) and (f5_enabled() if f5 is None else f5)
        if self.f5:
            self.layout, self.islands = f5_layout(expmem)
            self.blocks = [(c, c + (hi - lo) + (th[-1][1] if th else 0), lo) for lo, hi, c, th in self.layout]
            return
        self.blocks = blocks(expmem) if expmem else []
        self.islands = islands(expmem) if expmem else {}

    def to_copy(self, chip):
        """The copy of a chip address, or None if it is not copied."""
        if self.f5:
            for lo, hi, c, th in self.layout:
                if lo <= chip < hi:
                    g = 0
                    for t, n in th:
                        if t > chip - lo:
                            break
                        g = n
                    return c + chip - lo + g
            return None
        for lo, hi, start in self.blocks:
            if start <= chip < start + hi - lo:
                return lo + chip - start
        return None

    def island(self, pc):
        """True inside a JMP island (6 bytes)."""
        return any(a <= pc < a + 6 for a in self.islands)

    def to_chip(self, pc):
        """The chip original of a copied address, or an island's target; others unchanged."""
        for a, target in self.islands.items():
            if a <= pc < a + 6:
                return target
        if self.f5:
            for lo, hi, c, th in self.layout:
                size = hi - lo + (th[-1][1] if th else 0)
                if c <= pc < c + size:
                    q, g = pc - c, 0
                    for t, n in th:
                        if t + n > q:
                            break
                        g = n
                    return lo + q - g
            return pc
        for lo, hi, chip in self.blocks:
            if lo <= pc < hi:
                return chip + pc - lo
        return pc
