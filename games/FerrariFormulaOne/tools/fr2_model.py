#!/usr/bin/env python3
"""FR2 reference model of the blitter, mirroring src/FastRenderBlit.s.

Semantics follow the measurement emulator's cycle-exact blitter (UAE blitter.cpp,
custom.cpp), extended from tools/fr0_blits.py (verified on 279/280 real blits):
- BLTSIZE: h = bits 0-5 (0 = 64), v = bits 6-15 (0 = 1024).
- Pointers and modulos ignore bit 0.
- A/B shift history (aold/bold) is reset at blit start; B hold for a disabled B
  is whatever the last BLTBDAT write (or B read) produced: bdat_write().
- Fill carry restarts from FCI on every row; IFE with EFE behaves as EFE.
- Line mode (h = 2, B off): FR0's model of actually_do_blit; ASH, BSH, SIGN,
  APT, CPT and DPT are written back like the hardware.
- End state: pointers, ADAT/BDAT/CDAT hold the last words read.
"""

REGS = ('con0', 'con1', 'afwm', 'alwm', 'cpt', 'bpt', 'apt', 'dpt', 'cmod', 'bmod', 'amod', 'dmod', 'cdat', 'bdat', 'adat')


def s16(x):
    x &= 0xffff
    return x - 0x10000 if x & 0x8000 else x


def minterm(mt, a, b, c):
    r = 0
    for i in range(8):
        if mt >> i & 1:
            r |= (a if i & 4 else ~a) & (b if i & 2 else ~b) & (c if i & 1 else ~c)
    return r & 0xffff


def fill_word(d, fc, inclusive):
    x = d
    for k in range(16):
        m = 1 << k
        t = d & m
        if fc:
            x = x | m if inclusive else x ^ m
        if t:
            fc ^= 1
    return x & 0xffff, fc


class Blitter:
    def __init__(self, **kw):
        for k in REGS:
            setattr(self, k, 0)
        self.bold = 0
        self.bhold = 0
        for k, v in kw.items():
            setattr(self, k, v)

    def bdat_write(self, v):
        sh = self.con1 >> 12
        if self.con1 & 2:
            self.bhold = ((v << 16 | self.bold) >> (16 - sh)) & 0xffff
        else:
            self.bhold = ((self.bold << 16 | v) >> sh) & 0xffff
        self.bdat = v
        self.bold = v

    def blit(self, mem, size):
        """mem: object with rd(addr, ch) -> word and wr(addr, v)."""
        h = size & 0x3f or 64
        v = size >> 6 or 1024
        if self.con1 & 1:
            return self.line(mem, h, v)
        con0, con1 = self.con0, self.con1
        mt = con0 & 255
        desc = con1 & 2
        fill = con1 & 0x18
        inclusive = (con1 & 0x18) == 0x08
        ash, bsh = con0 >> 12, con1 >> 12
        ua, ub, uc, ud = (con0 & x for x in (0x800, 0x400, 0x200, 0x100))
        pa, pb, pc, pd = (p & ~1 for p in (self.apt, self.bpt, self.cpt, self.dpt))
        step = -2 if desc else 2
        sgn = -1 if desc else 1
        aold = 0
        bold = 0
        adat, cdat, bhold, bdat = self.adat, self.cdat, self.bhold, self.bdat
        mods = [s16(self.amod & ~1), s16(self.bmod & ~1), s16(self.cmod & ~1), s16(self.dmod & ~1)]
        for j in range(v):
            fc = 1 if con1 & 4 else 0
            for i in range(h):
                if ua:
                    adat = mem.rd(pa, 'A'); pa += step
                a = adat
                if i == 0:
                    a &= self.afwm
                if i == h - 1:
                    a &= self.alwm
                ah = ((a << 16 | aold) >> (16 - ash) if desc else (aold << 16 | a) >> ash) & 0xffff
                aold = a
                if ub:
                    bdat = mem.rd(pb, 'B'); pb += step
                    bhold = ((bdat << 16 | bold) >> (16 - bsh) if desc else (bold << 16 | bdat) >> bsh) & 0xffff
                    bold = bdat
                if uc:
                    cdat = mem.rd(pc, 'C'); pc += step
                d = minterm(mt, ah, bhold, cdat)
                if fill:
                    d, fc = fill_word(d, fc, inclusive)
                if ud:
                    mem.wr(pd, d); pd += step
            if ua: pa += sgn * mods[0]
            if ub: pb += sgn * mods[1]
            if uc: pc += sgn * mods[2]
            if ud: pd += sgn * mods[3]
        m32 = 0xffffffff
        if ua: self.apt = pa & m32
        if ub: self.bpt = pb & m32
        self.bold = bold
        if uc: self.cpt = pc & m32
        if ud: self.dpt = pd & m32
        self.adat, self.bdat, self.cdat, self.bhold = adat, bdat, cdat, bhold
        return 0

    def line(self, mem, h, v):
        con0, con1 = self.con0, self.con1
        if h != 2 or con0 & 0x400:
            return 1
        mt = con0 & 255
        SIGN, SUD, SUL, AUL, SING = 0x40, 0x10, 8, 4, 2
        ash, bsh = con0 >> 12, con1 >> 12
        apt, cpt, dpt = self.apt, self.cpt & ~1, self.dpt & ~1
        bdat, cdat = self.bdat, self.cdat
        amod, bmod, cmod = s16(self.amod & ~1), s16(self.bmod & ~1), s16(self.cmod & ~1)
        rot = lambda x, s: ((x >> s) | (x << (16 - s))) & 0xffff
        blineb = rot(bdat, bsh)
        onedot = 0
        for n in range(v):
            pixel = not (con1 & SING) or not onedot
            onedot = 1
            con1 = con1 | SIGN if s16(apt) < 0 else con1 & ~SIGN
            if con0 & 0x800:
                apt = (apt + (bmod if con1 & SIGN else amod)) & 0xffffffff
            if con0 & 0x200:
                cdat = mem.rd(cpt, 'C')
            d = minterm(mt, (self.adat & self.afwm) >> ash, 0xffff if blineb & 1 else 0, cdat)
            ovf = 0
            if not con1 & SIGN and not con1 & SUD:
                if con1 & SUL:
                    cpt -= 2 if ash == 0 else 0; ovf = -1
                else:
                    cpt += 2 if ash == 15 else 0; ovf = 1
            if con1 & SUD:
                if con1 & AUL:
                    cpt -= 2 if ash == 0 else 0; ovf = -1
                else:
                    cpt += 2 if ash == 15 else 0; ovf = 1
            ash = (ash + ovf) & 15
            if con0 & 0x200:
                if not con1 & SIGN and con1 & SUD:
                    cpt += -cmod if con1 & SUL else cmod; onedot = 0
                if not con1 & SUD:
                    cpt += -cmod if con1 & AUL else cmod; onedot = 0
            bsh = (bsh - 1) & 15
            blineb = rot(bdat, bsh)
            if pixel and con0 & 0x200:
                mem.wr(dpt, d)
            dpt = cpt
        self.con0 = (con0 & 0x0fff) | ash << 12
        self.con1 = (con1 & 0x0fff) | bsh << 12
        self.apt, self.cpt, self.dpt, self.cdat = apt, cpt & 0xffffffff, dpt & 0xffffffff, cdat
        self.bold = 0
        self.bhold = 0xffff if blineb & 1 else 0
        return 0


class Mem:
    """Sparse word memory; records touched word addresses per channel."""

    def __init__(self, data=None, base=0):
        self.data = data
        self.base = base
        self.touch = {}

    def rd(self, a, ch):
        self.touch.setdefault(ch, set()).add(a & 0xffffffff)
        if self.data is None:
            return 0
        o = (a - self.base) & 0xffffffff
        return self.data[o] << 8 | self.data[o + 1]

    def wr(self, a, v):
        self.touch.setdefault('D', set()).add(a & 0xffffffff)
        if self.data is None:
            return
        o = (a - self.base) & 0xffffffff
        self.data[o] = v >> 8
        self.data[o + 1] = v & 255
