"""Where the performance slave copies game code in its expansion memory (M1, S3).

Maps a copied instruction's address back to the original chip address, given the
allocated ws_ExpMem base (route_profile.py records it in route.json). The S3 ranges come
from whdload/renderer-relocs.i; the M1 blocks and the area offsets follow _hotcode and
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
    text = open(os.path.join(ROOT, 'whdload/renderer-relocs.i'), encoding='latin1').read()
    text = text.split('_render_ranges', 1)[1].split('dc.l\t0', 1)[0]
    for lo, hi, off in re.findall(r'dc\.l\s+\$(\w+)-\$3cb0,\$(\w+)-\$3cb0,\$(\w+)', text):
        lo, hi = int(lo, 16) - DISK_DELTA, int(hi, 16) - DISK_DELTA
        out.append((render + int(off, 16), render + int(off, 16) + hi - lo, lo))
    return out


def islands(expmem):
    """{island address: chip target} for S3's JMP islands (external word branches)."""
    k = _constants()
    render = expmem + k['STACKSIZE'] + k['HOTSIZE'] + k['TABLEMEM'] + k['RESTOREMEM']
    text = open(os.path.join(ROOT, 'whdload/renderer-relocs.i'), encoding='latin1').read()
    text = text.split('_render_branches', 1)[1].split('dc.l\t0', 1)[0]
    return {render + int(off, 16): int(target, 16) - DISK_DELTA for target, off in
            re.findall(r'dc\.l\s+\$\w+-\$3cb0,\$(\w+)-\$3cb0,\$(\w+)', text)}


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
