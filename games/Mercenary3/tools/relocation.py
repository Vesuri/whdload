"""Where the performance slave copies game code in its expansion memory (M1, S3, F2).

Maps a copied instruction's address back to the original chip address, given the
allocated ws_ExpMem base (route_profile.py records it in route.json). The S3/F2 ranges come
from whdload/renderer-relocs.i and renderer-f2.i; the M1 blocks and area offsets follow _hotcode and
_hotrenderer in whdload/Mercenary3.slave.asm. Copies keep the original instruction
lengths, so opcodes and offsets within a block match the chip original.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISK_DELTA = 0x3cb0


def _constants():
    text = open(os.path.join(ROOT, 'whdload/Mercenary3.slave.asm'), encoding='latin1').read()
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
        text = open(os.path.join(ROOT, 'whdload', filename), encoding='latin1').read()
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
        text = open(os.path.join(ROOT, 'whdload', filename), encoding='latin1').read()
        text = text.split(label, 1)[1].split('dc.l\t0', 1)[0]
        for target, off in re.findall(r'dc\.l\s+\$\w+-\$3cb0,\$(\w+)-\$3cb0,\$(\w+)', text):
            out[render + int(off, 16)] = int(target, 16) - DISK_DELTA
    return out


class Map:
    def __init__(self, expmem):
        self.blocks = blocks(expmem) if expmem else []
        self.islands = islands(expmem) if expmem else {}

    def island(self, pc):
        """True inside a JMP island (6 bytes)."""
        return any(a <= pc < a + 6 for a in self.islands)

    def to_chip(self, pc):
        """The chip original of a copied address, or an island's target; others unchanged."""
        for a, target in self.islands.items():
            if a <= pc < a + 6:
                return target
        for lo, hi, chip in self.blocks:
            if lo <= pc < hi:
                return chip + pc - lo
        return pc
