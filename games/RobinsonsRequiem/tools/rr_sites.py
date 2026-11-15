#!/usr/bin/env python3
"""The AGA slave's patch sites in the ECS game: rr_sites.py [-v] (docs/internals.md, "The
AGA's sites in the ECS game"; docs/performance.md, ECS plan step 6)

Both STARTs (tmp/game/RobinsonsRequiemAGA/data-aga/START and RobinsonsRequiem/data-ecs/START,
after make unpack) are the same program at other offsets. For each site the AGA slave checks
before it patches (SITES: the bytes it compares, from its hunk offset) this finds the ECS
site: the one place in any ECS hunk where the same bytes stand, with the longwords either
file relocates (absolute addresses) and the site's PC-relative displacements left out of
the comparison, and with as few bytes of the code around it as make the match unique
(up to 64 on each side). Every relocated operand and branch target of a matched site then
names its ECS counterpart (AGA hunk:offset to ECS hunk:offset), and an AGA target must
have one counterpart over all sites; the table also gives those operands.

Where the ECS code differs in the checked bytes themselves, BY_HAND gives the ECS site
found by reading both and its own bytes, which are checked instead; ECS_ONLY gives the ECS
game's own sites of an item (a load of the back screen the AGA START does not have), and
every ECS load of the back screen (movea.l <hunk 1 +$10>,An in hunks 0 and 2) must be a
site or in ECS_BACK_LEFT.

Prints the table (item, AGA site, ECS site, bytes, operands) and the operands' map, and
exits non-zero when a site that should match does not (EXPECT_NONE lists the ones that
have no ECS counterpart, each with why), matches more than once, maps an operand two
ways, or when a site given by hand or an ECS back screen load is not as listed. -v prints
the context each ambiguous match needed.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGA = ROOT / 'tmp/game/RobinsonsRequiemAGA/data-aga/START'
ECS = ROOT / 'tmp/game/RobinsonsRequiem/data-ecs/START'

# (item of docs/internals.md "AGA improvements", hunk, offset, bytes checked, PC-relative
# fields: (offset in the site, 'w' a word or 'b' a byte displacement, from the field's
# instruction at that offset - 2 for 'w' and - 1 for 'b'))
SITES = [
    (1, 0, 0x196, 10, ()),                      # move.l #0,<+$f4>
    (3, 0, 0x36ee, 4, ()),                      # the block allocator's movem.l d1/a0,-(sp)
    (3, 0, 0x3748, 6, ()),                      # the free: movem.l d0/a0,-(sp), movea.l d0,a0
    (3, 1, 0xa2b2, 6, ()),                      # jsr <hunk 0 +$36ee>: the chunky buffer
    (3, 1, 0xa2ce, 6, ()),                      # the renderer's tables
    (3, 1, 0xa30e, 6, ()),                      # the longword table, item 9's row table
    (4, 2, 0x2e84, 6, ()),                      # the conversion: move.w d6,<hunk 2 +$2db6>
    (5, 1, 0xe262, 48, ()),                     # the sky's row loop
    (6, 1, 0x257e, 6, ()),                      # movea.l <+$ee6c>,a3
    (6, 1, 0x6480, 6, ()),                      # movea.l <+$ee6c>,a0
    (6, 1, 0x250e, 6, ((2, 'w'), (5, 'b'))),    # bsr.w +$49b2, bra.s +$251a
    (6, 1, 0x49e8, 6, ()),                      # move.b <+$ee6a>,d0
    (6, 1, 0x4b54, 6, ()),                      # movem.l (sp)+,d0-a6, rts
    (7, 1, 0x4b8e, 6, ()),                      # jsr +$a3a6
    (8, 1, 0x4880, 6, ()),                      # movea.l <+$ed86>,a1
    (9, 1, 0xd908, 6, ()),                      # movea.l <+$a1de>,a2
    (9, 1, 0xde74, 8, ()),                      # move.w (22,a1,d1.w),d2, adda.l (16,a1,d1.w),a0
    (9, 1, 0xdf78, 8, ()),                      # the same in the other order
    (9, 1, 0x3b22, 8, ()),                      # lea (0,a1,d0.l),a1, move.w -964(a0),d1
    (9, 1, 0x3b74, 8, ()),                      # movea.l a0,a1, tst.b -1(a1), bpl.w
    (9, 1, 0x3540, 8, ()),                      # move.l #4,-988(a0)
    (10, 1, 0x30b4, 6, ()),                     # move.l a1,<+$ef3c>
    (10, 1, 0xbaac, 6, ()),                     # movea.l <+$ef3c>,a0
    (10, 1, 0xbe7e, 6, ()),
    (11, 0, 0x13c0, 8, ()),                     # btst #4,$dff01d: the wait for the new screen
    (11, 0, 0x13e0, 20, ()),                    # the swap: jsr +$13ce, jsr +$13f6, INTENA
    (11, 1, 0x4b30, 6, ()),                     # jsr <hunk 0 +$13e0>
    (11, 1, 0x49cc, 6, ()),                     # jsr <hunk 0 +$13c0>
    (11, 1, 0x4a0a, 6, ()),                     # tst.b <+$ed97>
    (11, 1, 0x4a14, 6, ()),                     # tst.b <+$ed99>
    (11, 1, 0x4a1a, 4, ((1, 'b'),)),            # bne.s +$4a14, addq.b #1,...
    (11, 1, 0x4a2c, 6, ()),                     # jsr +$525a
    (11, 1, 0x4a46, 6, ()),                     # jsr <hunk 2 +$4ec>
    (11, 1, 0x4a76, 10, ()),                    # move.l #<the rectangle list>,<+$ee08>
    (11, 1, 0x4a80, 6, ()),                     # clr.b <+$ee05>
    (11, 1, 0x4ada, 6, ()),                     # clr.b <+$edcf>
    (11, 1, 0x4b5e, 6, ()),                     # movea.l <+$ed86>,a1
    (11, 2, 0x2e02, 6, ()),                     # movea.l <+$10>,a1: the conversion's
] + [(11, h, o, 6, ()) for h, o in (               # the back screen's other loads (_gsites)
    (0, 0x1394), (0, 0x184e), (0, 0x1896), (0, 0x1994), (0, 0x1ad8), (0, 0x1b50),
    (0, 0x1b98), (0, 0x1bd4), (0, 0x1c26), (0, 0x1c66), (0, 0x1c9e), (0, 0x1e20),
    (0, 0x1e7e), (2, 0x3e), (2, 0x618), (2, 0x67e), (2, 0x884), (2, 0x9a4), (2, 0xa62),
    (2, 0x3c1e), (2, 0x3d5e), (2, 0x4364))] + [
    (12, 1, 0x4bd6, 10, ((8, 'w'),)),           # subq.b #1,<+$ef2a>, bne.w +$4be8
    (13, 1, 0x30e0, 8, ((6, 'w'),)),            # move.l d2,164(a0), bsr.w +$7b58
    (14, 1, 0xea4a, 6, ()),                     # adda.l (a2),a2, cmpi.b #28,(a2)
    (14, 1, 0x9540, 6, ()),                     # add.l d1,<+$ed60>
    (14, 1, 0x92ee, 6, ()),                     # sub.l d1,<+$ed60>
    (14, 1, 0x8d42, 6, ()),                     # move.l d0,<+$ed60>
    (15, 1, 0xd9ba, 0xdbb0 - 0xd9ba, ((0x1b0, 'w'),)),  # the landscape's inner loop (its
]                                               # checksum), bsr.w +$b6ea in it
# Sites without an ECS counterpart, and why.
NO_8 = "no such load in the ECS START, whose 2D routines draw 4 planes"
EXPECT_NONE = {
    (0, 0x196): "the ECS START keeps its fast pool (hunk 0 +$3be-$406: AllocMem of the "
                "sized pool, no discard)",
    (2, 0x2e84): "the ECS game's own 4-plane conversion (hunk 2 +$1a5e, ECS improvement 1)",
    (0, 0x1394): NO_8 + " (an 8-plane loop)",
    (0, 0x1b50): NO_8 + " (a mask of planes 0-3)",
    (0, 0x1b98): NO_8 + " (a mask of planes 0-3)",
    (0, 0x1bd4): NO_8 + " (a mask of planes 4-7)",
    (0, 0x1c9e): NO_8 + " (an 8-plane image's conversion)",
    (0, 0x1e20): NO_8 + " (planes 4-7)",
    (0, 0x1e7e): NO_8 + " (planes 0-3 after +$1e20's 4-7)",
    (2, 0x3c1e): "no such load in the ECS START: the AGA's 64,000-byte chunky screens",
    (2, 0x3d5e): "no such load in the ECS START: the AGA's 64,000-byte chunky screens",
    (2, 0x4364): "no such load in the ECS START: the AGA's 64,000-byte chunky screens",
}
# Sites whose ECS code differs in the bytes the AGA slave checks, found by reading both:
# the ECS site, its bytes to check (hex, .. a relocated byte) and why they differ.
BY_HAND = {
    (0, 0x3748): (0, 0x2c42, '48e7 8080 4a80', "the free tests for a null handle first "
                  "(tst.l d0, beq.w +$2c6e)"),
    (0, 0x1ad8): (0, 0x1366, '2879 .... ....', "the same loop after the drawing, word "
                  "arithmetic where the AGA's is long (the code after the load differs)"),
    (1, 0xea4a): (1, 0xd0a0, 'd5d2 0c12 0018', "image types 24 and 26 for the AGA's 28 and "
                  "30 (+$d0a2, +$d0aa)"),
}
# The ECS game's own sites of an item: its back screen's loads that have no AGA site.
ECS_ONLY = [
    (11, 0, 0x1232, '2879 .... ....', "the 4-plane copy of a planar image (bit 4 or 5 of its "
     "flags, +$1216)"),
]
# The ECS loads of <hunk 1 +$10> (the back screen, movea.l abs.l,An) that item 11 leaves:
# the VBL's pointer (the AGA's hunk 2 +$4fc).
ECS_BACK_LEFT = {(2, 0x2ba)}


def load(path):
    """START's hunks and their relocations ({offset: target hunk})."""
    d = Path(path).read_bytes()
    p = 0

    def word():
        nonlocal p
        p += 4
        return struct.unpack('>I', d[p - 4:p])[0]
    assert word() == 0x3f3
    while word():
        pass
    n, first, last = word(), word(), word()
    for _ in range(n):
        word()
    hunks, relocs = [], []
    while p < len(d):
        t = word() & 0x3fffffff
        if t in (0x3e9, 0x3ea):
            size = word() * 4
            hunks.append(d[p:p + size])
            relocs.append({})
            p += size
        elif t == 0x3eb:
            word()
            hunks.append(b'')
            relocs.append({})
        elif t == 0x3ec:
            while True:
                c = word()
                if not c:
                    break
                tgt = word()
                for _ in range(c):
                    relocs[-1][word()] = tgt
        elif t != 0x3f2:
            raise ValueError(f'hunk type {t:#x}')
    return hunks, relocs


class Image:
    def __init__(self, path):
        self.hunks, self.relocs = load(path)
        # per hunk: a byte mask, 0 where a relocated longword is
        self.mask = []
        for h, r in zip(self.hunks, self.relocs):
            m = bytearray(b'\1' * len(h))
            for o in r:
                m[o:o + 4] = b'\0\0\0\0'
            self.mask.append(m)

    def long(self, h, o):
        return struct.unpack('>I', self.hunks[h][o:o + 4])[0]


def free_bytes(img, h, lo, hi, pcrel_at):
    """(offset, byte) of hunk h's lo..hi that are neither relocated nor a displacement."""
    return [(j, img.hunks[h][j]) for j in range(lo, hi) if img.mask[h][j] and j not in pcrel_at]


def matches(aga, ecs, h, lo, hi, site, pcrel_at):
    """ECS (hunk, site offset) where AGA's lo..hi stand, relative to the site."""
    pat = [(j - site, b) for j, b in free_bytes(aga, h, lo, hi, pcrel_at)]
    if not pat:
        return []
    first_d, first_b = pat[0]
    out = []
    for eh, data in enumerate(ecs.hunks):
        m = ecs.mask[eh]
        start = data.find(bytes([first_b]))
        while start >= 0:
            x = start - first_d
            if 0 <= x + lo - site and x + hi - site <= len(data):
                ok = True
                for dj, b in pat:
                    y = x + dj
                    if m[y] and data[y] != b:
                        ok = False
                        break
                    if not m[y]:        # ECS relocates it: AGA must too
                        ok = False
                        break
                if ok:
                    out.append((eh, x))
            start = data.find(bytes([first_b]), start + 1)
    return out


def branch_words(img, h, lo, hi):
    """Offsets of the displacement words after even words $6x00 (Bcc.w, bra.w, bsr.w) in
    lo..hi: the context leaves them out, as code between may differ in size."""
    d, at = img.hunks[h], set()
    for j in range(lo - lo % 2, hi, 2):
        if j >= 0 and j + 3 < len(d) and d[j] >> 4 == 6 and d[j + 1] == 0:
            at.update((j + 2, j + 3))
    return at


def agrees(aga, ecs, h, lo, hi, site, pcrel_at, cand):
    eh, x = cand
    data, m = ecs.hunks[eh], ecs.mask[eh]
    if x + lo - site < 0 or x + hi - site > len(data):
        return False
    skip = pcrel_at | branch_words(aga, h, lo - 2, hi)
    for j, b in free_bytes(aga, h, lo, hi, skip):
        y = x + j - site
        if not m[y] or data[y] != b:
            return False
    return True


def reach(aga, ecs, h, site, n, pcrel_at, cand, most=64):
    """The bytes before plus after the site (up to `most` each) that agree at cand."""
    size = len(aga.hunks[h])
    before = after = 0
    while before < most and site - before - 2 >= 0 and \
            agrees(aga, ecs, h, site - before - 2, site, site, pcrel_at, cand):
        before += 2
    while after < most and site + n + after + 2 <= size and \
            agrees(aga, ecs, h, site + n, site + n + after + 2, site, pcrel_at, cand):
        after += 2
    return before + after


def check_bytes(aga, ecs, a, eh, eo, want, note, bad):
    """An ECS site given by hand: its bytes as `want` (.. relocated); the operands mapped
    to the AGA site a's (None: ECS only)."""
    ops, name = [], f'{eh}:+${eo:x}'
    for i, b in enumerate(want.replace(' ', '')[k:k + 2] for k in range(0, len(want.replace(' ', '')), 2)):
        y = eo + i
        if b == '..':
            if ecs.mask[eh][y]:
                bad.append(f'{name}: +{i} not relocated')
        elif not ecs.mask[eh][y] or ecs.hunks[eh][y] != int(b, 16):
            bad.append(f'{name}: +{i} is {ecs.hunks[eh][y]:02x}, not {b}')
    for o in sorted(ecs.relocs[eh]):
        if eo <= o < eo + len(want.replace(' ', '')) // 2:
            e = (ecs.relocs[eh][o], ecs.long(eh, o))
            if a is not None:
                ao = a[1] + o - eo
                if ao in aga.relocs[a[0]]:
                    aa = (aga.relocs[a[0]][ao], aga.long(a[0], ao))
                    note(aa, e, name)
                    ops.append(f'{aa[0]}:+${aa[1]:x}={e[0]}:+${e[1]:x}')
                    continue
            ops.append(f'-={e[0]}:+${e[1]:x}')
    return ops


def pcrel_bytes(fields, site):
    at = set()
    for o, kind in fields:
        at.update(range(site + o, site + o + (2 if kind == 'w' else 1)))
    return at


def main():
    verbose = '-v' in sys.argv
    for p in (AGA, ECS):
        if not p.exists():
            raise SystemExit(f'{p} missing: make unpack')
    aga, ecs = Image(AGA), Image(ECS)
    opmap, rows, bad = {}, [], []

    def note(a, e, where):
        if a in opmap and opmap[a][0] != e:
            bad.append(f'{where}: AGA {a[0]}:+${a[1]:x} maps to {e[0]}:+${e[1]:x}, before to '
                       f'{opmap[a][0][0]}:+${opmap[a][0][1]:x} ({opmap[a][1]})')
        opmap.setdefault(a, (e, where))

    for item, h, off, n, fields in SITES:
        name = f'{h}:+${off:x}'
        pcrel_at = pcrel_bytes(fields, off)
        size = len(aga.hunks[h])
        if (h, off) in BY_HAND:
            eh, eo, want, why = BY_HAND[(h, off)]
            rows.append((item, name, f'{eh}:+${eo:x}', len(want.split()) * 2,
                         ' '.join(check_bytes(aga, ecs, (h, off), eh, eo, want, note, bad)) +
                         f' (by hand: {why})'))
            continue
        hits = matches(aga, ecs, h, off, off + n, off, pcrel_at)
        ctx = 0
        if len(hits) > 1:
            # the candidate whose surrounding code agrees furthest (before plus after)
            scored = sorted(((reach(aga, ecs, h, off, n, pcrel_at, c), c) for c in hits),
                            reverse=True)
            ctx = scored[0][0]
            hits = [c for s, c in scored if s == ctx]
        if (h, off) in EXPECT_NONE:
            if hits and len(hits) == 1:
                bad.append(f'{name}: expected no ECS site, found {hits[0][0]}:+${hits[0][1]:x}')
            rows.append((item, name, '-', n, EXPECT_NONE[(h, off)]))
            continue
        if len(hits) != 1:
            bad.append(f'{name}: {len(hits)} ECS matches' +
                       (f', {ctx} bytes of context each' if hits else ''))
            rows.append((item, name, '?', n, ''))
            continue
        eh, eo = hits[0]
        ops = []
        for o in sorted(aga.relocs[h]):
            if off <= o < off + n:
                eo_op = eo + o - off
                a = (aga.relocs[h][o], aga.long(h, o))
                if eo_op not in ecs.relocs[eh]:
                    bad.append(f'{name}: AGA relocates +{o - off}, ECS does not')
                    continue
                e = (ecs.relocs[eh][eo_op], ecs.long(eh, eo_op))
                note(a, e, name)
                ops.append(f'{a[0]}:+${a[1]:x}={e[0]}:+${e[1]:x}')
        for fo, kind in fields:
            if kind == 'w':
                da = struct.unpack('>h', aga.hunks[h][off + fo:off + fo + 2])[0]
                de = struct.unpack('>h', ecs.hunks[eh][eo + fo:eo + fo + 2])[0]
            else:
                da = struct.unpack('>b', aga.hunks[h][off + fo:off + fo + 1])[0]
                de = struct.unpack('>b', ecs.hunks[eh][eo + fo:eo + fo + 1])[0]
            base = fo if kind == 'w' else fo + 1     # the PC the displacement is from
            a, e = (h, off + base + da), (eh, eo + base + de)
            note(a, e, name)
            ops.append(f'{a[0]}:+${a[1]:x}={e[0]}:+${e[1]:x}')
        rows.append((item, name, f'{eh}:+${eo:x}', n, ' '.join(ops)))
        if verbose:
            print(f'  {name}: {ctx} bytes of context')
    for item, eh, eo, want, why in ECS_ONLY:
        rows.append((item, '-', f'{eh}:+${eo:x}', len(want.split()) * 2,
                     ' '.join(check_bytes(aga, ecs, None, eh, eo, want, note, bad)) +
                     f' (ECS only: {why})'))
    # every ECS load of the back screen is a site or left on purpose
    ecs_sites = {tuple(int(x, 16) for x in r[2].replace('+$', '').split(':'))
                 for r in rows if r[2] not in ('-', '?')}
    for eh in (0, 2):
        for o, th in sorted(ecs.relocs[eh].items()):
            if th == 1 and ecs.long(eh, o) == 0x10 and o >= 2 and \
                    ecs.hunks[eh][o - 2] & 0xf1 == 0x20 and ecs.hunks[eh][o - 1] == 0x79:
                if (eh, o - 2) not in ecs_sites and (eh, o - 2) not in ECS_BACK_LEFT:
                    bad.append(f'ECS back screen load {eh}:+${o - 2:x} is no site')
    print(f'{"item":>4} {"AGA":10} {"ECS":10} {"bytes":>5}  operands (AGA=ECS) / why none')
    for item, a, e, n, ops in rows:
        print(f'{item:4d} {a:10} {e:10} {n:5d}  {ops}')
    print('operands:', ' '.join(f'{a[0]}:+${a[1]:x}={e[0]}:+${e[1]:x}'
                                for a, (e, _) in sorted(opmap.items())))
    aga_rows = [r for r in rows if r[1] != '-']
    found = sum(1 for r in aga_rows if r[2] not in ('-', '?'))
    print(f'{found} of {len(aga_rows)} AGA sites in the ECS game ({len(BY_HAND)} by hand), '
          f'{len(EXPECT_NONE)} without a counterpart, {len(ECS_ONLY)} ECS only')
    for b in bad:
        print('BAD', b)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
