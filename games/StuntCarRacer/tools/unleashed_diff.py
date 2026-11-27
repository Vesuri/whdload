#!/usr/bin/env python3
"""Align Stunt Car Racer Unleashed's reassembled code with the original program.

    python3 -I tools/unleashed_diff.py ORIGINAL EXE LISTING [--report OUT] [--json OUT]
        [--relocs OUT] [--asm src/relocs.s]

ORIGINAL is the decrypted main program as it lies at $e700 (tools/scr_extract.py). EXE and
LISTING are an Unleashed game build (StuntCarRacer.s assembled with -DWHDLOAD=1 as a hunk
executable, and vasm's -L listing of it). Both are disassembled into instruction
fingerprints that leave out what relocation changes (absolute addresses, PC-relative and
branch displacements, branch sizes) and keep everything else (opcodes, registers,
immediates, displacements). The two streams are aligned, and every stretch that differs
is reported with the original's addresses and instructions beside the Unleashed source
lines: the list of changes the patches have to reproduce.

The alignment also records, for every matched instruction with an absolute operand, the
original address beside the Unleashed symbol it became, which shows where Unleashed moved
a variable or pointed a reference elsewhere (--json).

--asm writes the fast copy's relocation table (docs/internals.md, "The fast copy"): the
matched references Unleashed relocates, the pointer tables of its Data section, and the
original's own references from a linear and a recursive-descent scan of its code; --relocs
lists every site with how it was found.
"""
import argparse
import bisect
import difflib
import json
import re
import struct
import sys

from capstone import Cs, CS_ARCH_M68K, CS_MODE_M68K_000, CS_MODE_BIG_ENDIAN
from capstone import m68k as M

BASE = 0xe700
# cmpi/addi/... #imm,Dn: vasm writes the Dn forms (cmp/add/...) of what the original has.
IMMEDIATE = re.compile(r'^(cmp|add|sub|and|or|eor)i(\.[bwl])$')
BRANCH = re.compile(r'^(b(?:ra|sr|hi|ls|cc|cs|ne|eq|vc|vs|pl|mi|ge|lt|gt|le|hs|lo))\.[sbwl]$')

# The original's own absolute references that the alignment cannot reach (code Unleashed
# rewrote or dropped: the interrupt vectors, self-modifying code, the copylock checks) are
# taken from a scan of the original code. These look like addresses in the image and are
# not: masks and constants, and data the linear disassembly ran through.
NOT_ADDRESSES = {
    0xe708,                     # move.l #$63ba8,d3: the checksum's length
    0x5a1ca, 0x5a1e4, 0x5a254, 0x5a26e, 0x5a2b4, 0x5a2ce, 0x5a5c6, 0x5a878, 0x5ae68,
    0x5b2e0, 0x5be5e, 0x5c30c, 0x5c326, 0x5c6d2, 0x5ff12, 0x62ecc, 0x6531c, 0x653ca,
    0x65764, 0x6577e, 0x65cb0,  # andi.l #$ffff
    0x59656, 0x59668,           # move.l #$1f800/#$1fc00,d5: a bit mask
    0x611f0,                    # suba.l #$14874,a0: the distance below (EXTRA_SITES)
    0x69332,                    # data
}
# What the hardware reads stays in chip memory at the original address: the copper list,
# the sprite and the samples, and the frame buffers (Unleashed's ChipData and ChipBSS).
CHIP = ((0xe74e, 0xe836), (0xf4b4, 0x1b6ca), (0x6a594, 0x80000))

# References no scan can see: an address computed from a base outside the image.
EXTRA_SITES = {
    0x611ea: 'movea.l #$79360,a0; suba.l #$14874,a0: the copylock key at $64aec',
}


def read_hunks(path):
    """The hunks of an executable: [(kind, bytes or size, [reloc32 (offset, target)])]."""
    d = open(path, 'rb').read()
    p = 0

    def L():
        nonlocal p
        v = struct.unpack_from('>L', d, p)[0]
        p += 4
        return v
    assert L() == 0x3f3
    while L():
        pass
    n = L()
    first, last = L(), L()
    for _ in range(last - first + 1):
        L()
    hunks = []
    cur = None
    while p < len(d):
        t = L() & 0x3fffffff
        if t in (0x3e9, 0x3ea):
            n = L() * 4
            cur = [t, d[p:p + n], []]
            p += n
        elif t == 0x3eb:
            cur = [t, L() * 4, []]
        elif t == 0x3ec:
            while True:
                n = L()
                if not n:
                    break
                tgt = L()
                for _ in range(n):
                    cur[2].append((L(), tgt))
        elif t == 0x3f2:
            hunks.append(cur)
            cur = None
        else:
            raise ValueError('hunk type %x at %x' % (t, p - 4))
    return hunks


def fingerprints(code, vma, relocs, absmax):
    """[(address, size, fingerprint, text, absolute operand values)] for a linear
    disassembly. relocs: the set of code offsets holding relocated longwords (Unleashed);
    for the original, an absolute value below absmax counts as an address."""
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000 | CS_MODE_BIG_ENDIAN)
    md.detail = True
    out = []
    off = 0
    while off < len(code) - 1:
        ins = None
        for ins in md.disasm(code[off:off + 10], vma + off, 1):
            pass
        if ins is None:
            out.append((vma + off, 2, ('dc.w', code[off:off + 2].hex()), 'dc.w $' + code[off:off + 2].hex(), ()))
            off += 2
            continue
        # Unleashed: the relocated longwords inside this instruction, by value; an operand
        # is an address when its value is one of them.
        rv = {}
        if relocs is not None:
            for r in range(off, off + ins.size - 3):
                if relocs[r] is not None:
                    rv[struct.unpack_from('>L', code, r)[0]] = relocs[r]
        if ins.id == 0:
            out.append((vma + off, 2, ('dc.w', code[off:off + 2].hex()), 'dc.w $' + code[off:off + 2].hex(), ()))
            off += 2
            continue
        fp = [IMMEDIATE.sub(r'\1\2', BRANCH.sub(r'\1', ins.mnemonic))]
        absv = []
        for op in ins.operands:
            if op.type == M.M68K_OP_REG:
                fp.append(('r', op.reg))
            elif op.type == M.M68K_OP_IMM or op.type == M.M68K_OP_MEM and op.address_mode == M.M68K_AM_IMMEDIATE:
                v = op.imm & 0xffffffff
                if (v in rv if relocs is not None else BASE <= v < absmax) and ins.op_size.size == 4:
                    fp.append('#A')
                    absv.append(v)
                else:
                    fp.append(('#', v))
            elif op.type == M.M68K_OP_BR_DISP:
                fp.append('BR')
            elif op.type == M.M68K_OP_MEM:
                am = op.address_mode
                if am in (M.M68K_AM_ABSOLUTE_DATA_SHORT, M.M68K_AM_ABSOLUTE_DATA_LONG):
                    v = op.imm & 0xffffffff
                    if am == M.M68K_AM_ABSOLUTE_DATA_SHORT and v & 0x8000:
                        v |= 0xffff0000
                    if (v in rv if relocs is not None else v < absmax):
                        fp.append('A')
                        absv.append(v)
                    else:
                        fp.append(('abs', v))
                elif am in (M.M68K_AM_PCI_DISP, M.M68K_AM_PCI_INDEX_8_BIT_DISP, M.M68K_AM_PCI_INDEX_BASE_DISP):
                    fp.append(('pc', am, op.mem.index_reg))
                else:
                    fp.append(('m', am, op.mem.base_reg, op.mem.index_reg, op.mem.index_size, op.mem.disp))
            else:
                fp.append(('o', op.type, op.reg))
        if relocs is not None:
            absv = ['%d:%x' % (rv[v], v) for v in absv]
        else:
            absv = ['%x' % v for v in absv]
        out.append((ins.address, ins.size, tuple(fp), (ins.mnemonic + ' ' + ins.op_str).strip(), tuple(absv)))
        off += ins.size
    return out


def read_listing(path):
    """{code offset: (source line number, source text)} for section 00."""
    rx = re.compile(r'^00:([0-9A-F]{8}) [0-9A-F ]*\t\s*(\d+): (.*)$')
    lines = {}
    for line in open(path, encoding='latin-1'):
        m = rx.match(line.rstrip('\n'))
        if m:
            lines.setdefault(int(m.group(1), 16), (int(m.group(2)), m.group(3)))
    return lines


def write_asm(path, sites, orig, image_end):
    """The relocation table: every site where the original holds an address inside the
    image that Unleashed relocated to memory the program may move to (its code, its copy of
    the original data, its Data and BSS sections). What Unleashed put in chip memory (the
    copper list, samples, sprites, frame buffers: its ChipData and ChipBSS) stays at the
    original address, and so does everything outside the image."""
    keep = {}
    for site, ov, h, uv, (n, t), how in sites:
        if h in (0, 1, 2, 4) and (BASE <= ov < image_end or how == 'X'):
            keep[site] = (ov, h, n, t.strip())
    with open(path, 'w') as f:
        f.write('; Generated by tools/unleashed_diff.py --asm (docs/development.md): do not edit.\n')
        f.write('; The main program\'s absolute references into its own image ($%05x-$%05x) that\n' % (BASE, image_end))
        f.write('; move with it, in address order. Each word is the distance from the previous site\n')
        f.write('; (the first from $%05x); 0 is followed by a longword distance, and 0, 0.l ends it.\n' % BASE)
        f.write('; The comment is the site, the value there and the Unleashed source line or the\n')
        f.write('; original instruction.\n')
        f.write('relocTable:\n')
        prev = BASE
        for site in sorted(keep):
            ov, h, n, t = keep[site]
            d = site - prev
            assert d > 0 or site == BASE
            t = t.replace('\t', ' ')
            t = ('%d: ' % n if n else '' if t.startswith('Unleashed ') else 'original: ') + t
            if d < 0x10000:
                f.write('\tdc.w\t$%04x\t\t; $%05x $%05x %s\n' % (d, site, ov, t))
            else:
                f.write('\tdc.w\t0\n\tdc.l\t$%x\t\t; $%05x $%05x %s\n' % (d, site, ov, t))
            prev = site
        f.write('\tdc.w\t0\n\tdc.l\t0\n')
    print('%s: %d sites' % (path, len(keep)), file=sys.stderr)


def read_symbols(listing):
    """[(name, section, offset)] from the listing's symbol table."""
    rx = re.compile(r'^(\S+)\s+([0-9A-F]{2}):([0-9A-F]{8})$')
    syms = []
    on = False
    for line in open(listing, encoding='latin-1'):
        line = line.rstrip('\n')
        if line.startswith('Symbols by name'):
            on = True
            continue
        if line.startswith('Symbols by value'):
            break
        m = on and rx.match(line)
        if m:
            syms.append((m.group(1), int(m.group(2), 16), int(m.group(3), 16)))
    return syms


def matched_references(sites):
    """{(Unleashed hunk, offset): {original values}} of the references the alignment matched."""
    ref = {}
    for site, ov, h, uv, _, how in sites:
        if how in ('M', 'R'):
            ref.setdefault((h, uv), set()).add(ov)
    return ref


def data_hunk_sites(hunks, listing, sites, orig, image_end):
    """The relocated longwords of Unleashed's Data section (hunk 2: pointer tables such as
    mountainSilhouetteTable) at their original addresses. A label there whose matched
    references all hold one original value places the longwords behind it, up to the next
    label; a site counts only if the original holds an address inside the image there."""
    ref = matched_references(sites)
    labels = sorted((off, min(ref[(2, off)])) for _, sec, off in read_symbols(listing)
                    if sec == 2 and len(ref.get((2, off), ())) == 1)
    out = []
    for r, h in hunks[2][2]:
        i = bisect.bisect_right([o for o, _ in labels], r) - 1
        if i < 0:
            continue
        site = labels[i][1] + r - labels[i][0]
        v = struct.unpack_from('>L', orig, site - BASE)[0]
        if BASE <= v < image_end:
            out.append((site, v, h, struct.unpack_from('>L', hunks[2][1], r)[0], (0, 'Unleashed Data +%05x' % r), 'H'))
    return out


def write_symbols(path, listing, u2o, sites):
    """NAME ORIGINAL HOW for every label in the listing's symbol table. HOW: 'c' a matched
    instruction of the code; 'n' between two matched instructions the same distance apart;
    'd' Unleashed's copy of the original data ($e700 + offset - 4); 'r' a relocated
    reference that the alignment matched to an original value; '-' none (Unleashed's own)."""
    syms = read_symbols(listing)
    ref = matched_references(sites)
    keys = sorted(u2o)
    with open(path, 'w') as f:
        for name, sec, off in sorted(syms, key=lambda s: (s[1], s[2], s[0])):
            if sec == 0:
                if off in u2o:
                    o, how = u2o[off], 'c'
                else:
                    i = bisect.bisect_left(keys, off)
                    o, how = None, '-'
                    if 0 < i < len(keys):
                        a0, a1 = keys[i - 1], keys[i]
                        if u2o[a1] - u2o[a0] == a1 - a0:
                            o, how = u2o[a0] + off - a0, 'n'
                        else:
                            # A changed stretch: where the matched instructions on either
                            # side put it, for a reader to settle.
                            how = '- after $%05x+%x, before $%05x-%x' % (
                                u2o[a0], off - a0, u2o[a1], a1 - off)
            elif sec == 1:
                o, how = BASE + off - 4, 'd'
            else:
                v = ref.get((sec, off))
                o, how = (min(v), 'r') if v and len(v) == 1 else (None, '-')
            f.write('%-40s %d:%05x %s %s\n' % (name, sec, off, '$%05x' % o if o is not None else '-', how))


def reachable(orig, ranges, image_end):
    """{address: (size, text, absolute operand values)} for every instruction a recursive
    descent reaches from the start ($e700 and the trap #0 entry $e73c) and from every
    absolute jsr/jmp target in the linear disassembly: the code a linear disassembly
    misreads behind data words in the instruction stream (flags the game modifies)."""
    md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000 | CS_MODE_BIG_ENDIAN)
    md.detail = True

    def dec(a):
        for ins in md.disasm(orig[a - BASE:a - BASE + 10], a, 1):
            return ins

    todo = [BASE, 0xe73c]
    for s0, e0 in ranges:
        for oa, size, fp, text, absv in fingerprints(orig[s0 - BASE:e0 - BASE], s0, None, image_end):
            if text.startswith(('jsr', 'jmp')) and absv:
                todo.append(int(absv[0], 16))
    out = {}
    while todo:
        a = todo.pop()
        while BASE <= a < image_end and a not in out:
            ins = dec(a)
            if ins is None or ins.id == 0:
                break
            f = fingerprints(orig[a - BASE:a - BASE + ins.size], a, None, image_end)
            out[a] = (ins.size, f[0][3] if f else '', f[0][4] if f else ())
            m = ins.mnemonic.split('.')[0]
            for op in ins.operands:
                if op.type == M.M68K_OP_BR_DISP:
                    todo.append(ins.address + 2 + op.br_disp.disp)
                elif (op.type == M.M68K_OP_MEM and op.address_mode == M.M68K_AM_ABSOLUTE_DATA_LONG
                      and m in ('jsr', 'jmp')):
                    todo.append(op.imm & 0xffffffff)
            if m in ('rts', 'rte', 'rtr', 'jmp', 'bra', 'illegal'):
                break
            a += ins.size
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument('original')
    p.add_argument('exe')
    p.add_argument('listing')
    p.add_argument('--ranges', default='e700-f472,1b74a-1b900,1ba08-1baf8,57000-6a166',
                   help='the original code ranges, hex start-end,...')
    p.add_argument('--report')
    p.add_argument('--json')
    p.add_argument('--relocs', help='write the relocation sites: matched, then unmatched')
    p.add_argument('--asm', help='write the relocation table source (src/relocs.s)')
    p.add_argument('--symbols', help='write every Unleashed label with its original address')
    p.add_argument('--image-end', type=lambda v: int(v, 16), default=0x722e0,
                   help='the end of the program image the table relocates (hex)')
    a = p.parse_args()

    orig = open(a.original, 'rb').read()
    ranges = [tuple(int(x, 16) for x in r.split('-')) for r in a.ranges.split(',')]
    end = ranges[-1][1]
    hunks = read_hunks(a.exe)
    code = hunks[0][1]
    relocs = [None] * (len(code) + 4)
    for o, h in hunks[0][2]:
        relocs[o] = h
    lst = read_listing(a.listing)

    O = []
    for s, e in ranges:
        O += fingerprints(orig[s - BASE:e - BASE], s, None, 0x80000)
    U = fingerprints(code, 0, relocs, 0)
    sm = difflib.SequenceMatcher(None, [x[2] for x in O], [x[2] for x in U], autojunk=False)
    ops = sm.get_opcodes()

    src_offsets = sorted(lst)

    def src(uoff):
        i = bisect.bisect_right(src_offsets, uoff) - 1
        return lst[src_offsets[i]] if i >= 0 else (0, '')

    out = open(a.report, 'w') if a.report else sys.stdout
    matched = 0
    absmap = {}
    sites = []
    covered = set()
    for tag, i1, i2, j1, j2 in ops:
        if tag == 'equal':
            for k in range(i2 - i1):
                oa, ua, usize = O[i1 + k][0], U[j1 + k][0], U[j1 + k][1]
                for r in range(ua, ua + usize - 3):
                    if relocs[r] is not None:
                        covered.add(r)
                        site = oa + r - ua
                        ov = struct.unpack_from('>L', orig, site - BASE)[0]
                        uv = struct.unpack_from('>L', code, r)[0]
                        sites.append((site, ov, relocs[r], uv, src(ua), 'M'))
            matched += i2 - i1
            for k in range(i2 - i1):
                ov, uv = O[i1 + k][4], U[j1 + k][4]
                for x, y in zip(ov, uv):
                    absmap.setdefault(x, set()).add(y)
            continue
        if tag == 'delete' and i2 - i1 > 40:
            # Original stretches with no Unleashed counterpart at all: data, or code Unleashed
            # replaced wholesale. Listed in one line.
            print('-- original only $%05x-$%05x (%d instructions)' % (O[i1][0], O[i2 - 1][0] + O[i2 - 1][1], i2 - i1), file=out)
            continue
        if tag == 'insert' and j2 - j1 > 200:
            print('-- Unleashed only at +%05x, lines %d-%d (%d instructions)' % (U[j1][0], src(U[j1][0])[0], src(U[j2 - 1][0])[0], j2 - j1), file=out)
            continue
        oa = O[i1][0] if i1 < i2 else (O[i1][0] if i1 < len(O) else end)
        print('== %s at original $%05x, Unleashed +%05x' % (tag, oa, U[j1][0] if j1 < len(U) else len(code)), file=out)
        for k in range(i1, i2):
            print('   - $%05x  %s' % (O[k][0], O[k][3]), file=out)
        seen = set()
        for k in range(j1, j2):
            n, t = src(U[k][0])
            if n not in seen:
                seen.add(n)
                print('   + %6d  %s' % (n, t.strip()), file=out)
    print('matched %d of %d original and %d Unleashed instructions' % (matched, len(O), len(U)), file=sys.stderr)

    # Resynchronise what the alignment lost: an Unleashed instruction with a relocated
    # operand outside the matched stretches (usually beside a data island the linear
    # disassembly of the original ran through) is looked for byte for byte, relocated
    # longwords masked, near where the neighbouring matches put it.
    u2o = {}
    for tag, i1, i2, j1, j2 in ops:
        if tag == 'equal':
            for k in range(i2 - i1):
                u2o[j1 + k] = O[i1 + k][0]
    uaddr = [x[0] for x in U]
    matched_u = sorted(u2o)
    resynced = 0
    for j, (ua, usize, _, utext, _) in enumerate(U):
        rs = [r for r in range(ua, ua + usize - 3) if relocs[r] is not None and r not in covered]
        if not rs:
            continue
        i = bisect.bisect_left(matched_u, j) - 1
        if i < 0:
            continue
        jm = matched_u[i]
        guess = u2o[jm] + ua - uaddr[jm]
        ub = bytearray(code[ua:ua + usize])
        for r in rs:
            ub[r - ua:r - ua + 4] = b'\0\0\0\0'
        hits = []
        for o in range(max(BASE, guess - 512) & ~1, min(end, guess + 512), 2):
            ob = bytearray(orig[o - BASE:o - BASE + usize])
            ok = True
            for r in rs:
                v = struct.unpack_from('>L', ob, r - ua)[0]
                if not BASE <= v < 0x80000:
                    ok = False
                ob[r - ua:r - ua + 4] = b'\0\0\0\0'
            if ok and ob == ub:
                # An operand into Unleashed's copy of the original data must be the same
                # address; other targets cannot be checked here.
                for r in rs:
                    v = struct.unpack_from('>L', orig, o - BASE + r - ua)[0]
                    uv = struct.unpack_from('>L', code, r)[0]
                    if relocs[r] == 1 and v != uv - 4 + BASE:
                        ok = False
                if ok:
                    hits.append(o)
        if len(hits) == 1:
            for r in rs:
                covered.add(r)
                site = hits[0] + r - ua
                ov = struct.unpack_from('>L', orig, site - BASE)[0]
                uv = struct.unpack_from('>L', code, r)[0]
                sites.append((site, ov, relocs[r], uv, src(ua), 'R'))
                resynced += 1
    print('resynchronised %d relocations' % resynced, file=sys.stderr)
    # The original's own references the alignment left out.
    have = set(x[0] for x in sites)
    scanned = 0
    for s0, e0 in ranges:
        for oa, size, fp, text, absv in fingerprints(orig[s0 - BASE:e0 - BASE], s0, None, a.image_end):
            for r in range(oa, oa + size - 3):
                v = struct.unpack_from('>L', orig, r - BASE)[0]
                if ('%x' % v in absv and BASE <= v and r not in have and r not in NOT_ADDRESSES
                        and not any(c0 <= v < c1 for c0, c1 in CHIP)):
                    sites.append((r, v, 0, 0, (0, text), 'O'))
                    have.add(r)
                    scanned += 1
    for oa, (size, text, absv) in sorted(reachable(orig, ranges, a.image_end).items()):
        for r in range(oa, oa + size - 3):
            v = struct.unpack_from('>L', orig, r - BASE)[0]
            if ('%x' % v in absv and BASE <= v and r not in have and r not in NOT_ADDRESSES
                    and not any(c0 <= v < c1 for c0, c1 in CHIP)):
                sites.append((r, v, 0, 0, (0, text), 'D'))
                have.add(r)
                print('recursive descent: $%05x %s' % (oa, text), file=sys.stderr)
    data = [x for x in data_hunk_sites(hunks, a.listing, sites, orig, a.image_end) if x[0] not in have]
    sites += data
    have.update(x[0] for x in data)
    print('added %d references from the Data section' % len(data), file=sys.stderr)
    for r, why in EXTRA_SITES.items():
        v = struct.unpack_from('>L', orig, r - BASE)[0]
        sites.append((r, v, 0, 0, (0, why), 'X'))
    print('added %d references from the original code' % scanned, file=sys.stderr)
    if a.relocs:
        with open(a.relocs, 'w') as f:
            for site, ov, h, uv, (n, t), how in sites:
                print('%s %05x %08x %d:%05x %6d %s' % (how, site, ov, h, uv, n, t.strip()), file=f)
            for r, h in enumerate(relocs):
                if h is not None and r not in covered:
                    n, t = src(r)
                    uv = struct.unpack_from('>L', code, r)[0]
                    print('U +%05x %d:%05x %6d %s' % (r, h, uv, n, t.strip()), file=f)
            for hi, hk in enumerate(hunks[1:], 1):
                for r, h in hk[2]:
                    print('H%d +%05x %d' % (hi, r, h), file=f)
    if a.asm:
        write_asm(a.asm, sites, orig, a.image_end)
    if a.symbols:
        write_symbols(a.symbols, a.listing, {uaddr[j]: o for j, o in u2o.items()}, sites)
    if a.json:
        json.dump({k: sorted(vs) for k, vs in sorted(absmap.items(), key=lambda kv: int(kv[0], 16))}, open(a.json, 'w'), indent=0)


if __name__ == '__main__':
    sys.exit(main())
