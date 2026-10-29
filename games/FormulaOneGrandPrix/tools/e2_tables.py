#!/usr/bin/env python3
"""E2: which of hunk 2's code may run from a fast-RAM copy, and the patch table.

  e2_tables.py [--out tmp/slave/include/e2.i] [--report tmp/...json]

Recursive descent over f1gp's hunks 0 and 2 from the program entry and the slave's hunk 2
code targets (F1GP.s: c2_target_h2 to c2_target_end, c2_hud_targets), following branches,
BSR, and JSR/JMP to absolute (relocated) or PC-relative targets. In the copy, a routine
runs from fast RAM if it is entered through a redirected absolute JSR/JMP; everything it
reaches PC-relatively (branches, BSR, PC-relative JSR/JMP) also runs from the copy. That
relative closure must not contain a hazard:
- a PC-relative LEA/PEA of anything but a known instruction (the address escapes: writes
  through it would land in the copy);
- a PC-relative read of data that is not constant (constant: the bytes between two pieces
  of code, reached by no relocation and no PC-relative LEA/PEA);
- a PC-relative computed JSR/JMP (d8,PC,Xn) (its targets are not followed);
- code written through an absolute address (the copy would keep the old instruction).
Entries whose closure has none are redirected: the table lists every relocated JSR/JMP
operand (hunk 0 or 2) to such an entry. Slave targets must all be safe (or the build
fails). The copied span covers the safe closures. The output contains offsets derived from
the game and must stay under tmp/.
"""
import argparse
import collections
import json
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capstone import CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000, Cs   # noqa: E402
from capstone.m68k import (M68K_AM_ABSOLUTE_DATA_LONG, M68K_AM_PCI_DISP,        # noqa: E402
                           M68K_AM_PCI_INDEX_8_BIT_DISP, M68K_AM_PCI_INDEX_BASE_DISP,
                           M68K_OP_MEM)
from slave_inputs import ROOT, verify                                          # noqa: E402

GAME = ROOT/'tmp/game/FormulaOneGrandPrix4Disk/data/f1gp'
SOURCE = ROOT/'whdload/F1GP.s'
BRANCH = {'bra', 'bsr', 'bhi', 'bls', 'bcc', 'bcs', 'bne', 'beq', 'bvc', 'bvs', 'bpl', 'bmi',
          'bge', 'blt', 'bgt', 'ble', 'bhs', 'blo'}
END = {'rts', 'rte', 'rtr', 'jmp', 'bra', 'illegal'}
PC_INDEX = (M68K_AM_PCI_INDEX_8_BIT_DISP, M68K_AM_PCI_INDEX_BASE_DISP)
# Instructions whose last memory operand is only read.
READ_ONLY = ('cmp', 'tst', 'btst', 'chk')
# Below this, hunk 2 holds the copper list, interrupt, keyboard and audio code (h2+$0-$93F)
# and the samples and data before the main code; entries whose closure starts below it
# stay in chip, so the copy covers the main code only.
FLOOR = 0x1d000


def hunks():
    data = GAME.read_bytes()
    u = lambda p: struct.unpack_from('>I', data, p)[0]
    p, h, out, relocs = 20+4*(u(16)+1), 0, {}, collections.defaultdict(dict)
    while p < len(data):
        kind = u(p) & 0x3fffffff
        p += 4
        if kind in (1001, 1002):
            n = u(p)*4
            out[h] = data[p+4:p+4+n]
            p += 4+n
        elif kind == 1003:
            out[h] = None
            p += 4
        elif kind == 1004:
            while u(p):
                count, target = u(p), u(p+4)
                for k in range(count):
                    relocs[h][u(p+8+4*k)] = target
                p += 8+4*count
            p += 4
        elif kind == 1010:
            h += 1
        else:
            raise ValueError(f'unsupported hunk record {kind}')
    return out, relocs


def slave_targets():
    """The slave's hunk 2 code addresses: jump and continuation targets."""
    text = SOURCE.read_text()
    found = []
    for start in ('c2_target_h2', 'c2_hud_targets'):
        lines = text[text.index('\n'+start+'\n')+len(start)+2:].splitlines()
        for line in lines:
            words = line.split(';')[0].split()
            if 'dc.l' in words:
                found += [int(x, 16) for x in re.findall(r'\$([0-9a-f]+)', words[-1])]
            elif words[:1] != ['dc.w']:
                break
    return found


class Code:
    def __init__(self):
        self.hunks, self.relocs = hunks()
        self.cs = Cs(CS_ARCH_M68K, CS_MODE_M68K_000 | CS_MODE_BIG_ENDIAN)
        self.cs.detail = True
        self.insn = {0: {}, 2: {}}

    def decode(self, h, at):
        code = self.hunks[h]
        return next(self.cs.disasm(code[at:at+16], at, count=1), None)

    def flow(self, h, i):
        """(relative targets, absolute (hunk, offset) target or None)."""
        op = i.mnemonic.split('.')[0]
        if op in BRANCH or op.startswith('db'):
            return [i.operands[-1].br_disp.disp + i.address + 2], None
        if op in ('jsr', 'jmp'):
            o = i.operands[0]
            if o.address_mode == M68K_AM_PCI_DISP:
                return [i.address + 2 + o.mem.disp], None
            if o.address_mode == M68K_AM_ABSOLUTE_DATA_LONG and i.address+2 in self.relocs[h]:
                return [], (self.relocs[h][i.address+2], o.imm)
        return [], None

    def descend(self, seeds):
        work = list(seeds)
        while work:
            h, at = work.pop()
            while at not in self.insn[h]:
                if at & 1 or at >= len(self.hunks[h]):
                    raise ValueError(f'bad code address h{h}+{at:x}')
                i = self.decode(h, at)
                if i is None:
                    raise ValueError(f'undecodable h{h}+{at:x}')
                self.insn[h][at] = i
                relative, absolute = self.flow(h, i)
                work += [(h, t) for t in relative]
                if absolute and absolute[0] in self.insn:
                    work.append(absolute)
                if i.mnemonic.split('.')[0] in END:
                    break
                at += i.size

    def starts(self, h):
        return self.insn[h]

    def gaps(self, h):
        """Sorted (start, end) of the bytes between known instructions."""
        spans = sorted((a, a+i.size) for a, i in self.insn[h].items())
        out, last = [], 0
        for a, z in spans:
            if a > last:
                out.append((last, a))
            last = max(last, z)
        out.append((last, len(self.hunks[h])))
        return out


def analyse():
    verify()
    code = Code()
    targets = slave_targets()
    code.descend([(0, 0)] + [(2, t) for t in targets])
    h2 = code.insn[2]
    inside = {}                       # h2 byte -> instruction start
    for a, i in h2.items():
        for b in range(a, a+i.size):
            inside[b] = a
    gaps = code.gaps(2)
    gap_of = lambda t: next(((a, z) for a, z in gaps if a <= t < z), None)
    # Absolute references into hunk 2 (relocated longwords anywhere, by target).
    referenced = collections.defaultdict(list)
    for h, table in code.relocs.items():
        for at, target in table.items():
            if target == 2:
                referenced[struct.unpack_from('>I', code.hunks[h], at)[0]].append((h, at))
    lea_gaps = set()
    for a, i in h2.items():
        if i.mnemonic.split('.')[0] in ('lea', 'pea') and i.operands[0].address_mode == M68K_AM_PCI_DISP:
            g = gap_of(a+2+i.operands[0].mem.disp)
            if g:
                lea_gaps.add(g)
    hazards = {}
    for a, i in h2.items():
        op = i.mnemonic.split('.')[0]
        if op in BRANCH or op.startswith('db'):
            continue
        for n, o in enumerate(i.operands):
            if o.type != M68K_OP_MEM:
                continue
            if o.address_mode in PC_INDEX and op in ('jsr', 'jmp'):
                hazards[a] = 'PC-relative computed jump'
            elif o.address_mode == M68K_AM_PCI_DISP and op in ('jsr', 'jmp'):
                continue
            elif o.address_mode == M68K_AM_PCI_DISP or o.address_mode in PC_INDEX:
                t = a + 2 + o.mem.disp
                if op in ('lea', 'pea'):
                    if t not in h2:
                        hazards[a] = f'PC-relative address of data h2+{t:x}'
                    continue
                g = gap_of(t)
                if g is None:
                    continue          # reads an instruction: identical in the copy
                if g in lea_gaps or any(g[0] <= r < g[1] for r in referenced):
                    hazards[a] = f'PC-relative read of written data h2+{t:x}'
    # Code written through an absolute address.
    for h in (0, 2):
        for a, i in code.insn[h].items():
            op = i.mnemonic.split('.')[0]
            if op in READ_ONLY or op in ('jsr', 'jmp', 'lea', 'pea') or not i.operands:
                continue
            o = i.operands[-1]
            at = a + i.size - 4       # the destination's address extension
            if (o.type == M68K_OP_MEM and o.address_mode == M68K_AM_ABSOLUTE_DATA_LONG
                    and code.relocs[h].get(at) == 2):
                t = struct.unpack_from('>I', code.hunks[h], at)[0]
                if t in inside:
                    hazards[inside[t]] = f'written by h{h}+{a:x}'

    def closure(entry):
        seen, work = set(), [entry]
        while work:
            at = work.pop()
            while at not in seen:
                seen.add(at)
                i = h2[at]
                relative, _ = code.flow(2, i)
                work += relative
                # A PC-relative address of code can be jumped to later, from the copy.
                if i.mnemonic.split('.')[0] in ('lea', 'pea') and i.operands[0].address_mode == M68K_AM_PCI_DISP:
                    t = at + 2 + i.operands[0].mem.disp
                    if t in h2:
                        work.append(t)
                if i.mnemonic.split('.')[0] in END:
                    break
                at += i.size
        return seen

    entries = set(targets)
    sites = []                        # (hunk, operand offset, target)
    for h in (0, 2):
        for a, i in code.insn[h].items():
            if i.mnemonic.split('.')[0] in ('jsr', 'jmp'):
                _, absolute = code.flow(h, i)
                if absolute and absolute[0] == 2:
                    entries.add(absolute[1])
                    sites.append((h, a+2, absolute[1]))
    safe, unsafe, below, spans = set(), {}, set(), set()
    for e in sorted(entries):
        reach = closure(e)
        bad = sorted(reach & hazards.keys())
        if bad:
            unsafe[e] = [f'h2+{b:x}: {hazards[b]}' for b in bad[:3]]
        elif min(reach) < FLOOR:
            if max(reach) >= FLOOR:
                raise SystemExit(f'h2+{e:x} reaches across the floor')
            below.add(e)
        else:
            safe.add(e)
            spans |= reach
    # The slave redirects its targets by range, so each must be safe or wholly below.
    failed = [t for t in targets if t not in safe and t not in below]
    if failed:
        raise SystemExit('slave targets reach hazards: ' + ', '.join(
            f'h2+{t:x} ({unsafe[t][0]})' for t in failed))
    patches = sorted((h, at) for h, at, t in sites if t in safe)
    low = min(spans) & ~0xf
    high = max(a+h2[a].size for a in spans)
    # PC-relative constant reads inside the closures stay inside the span.
    for a in spans:
        for o in h2[a].operands:
            if o.type == M68K_OP_MEM and (o.address_mode == M68K_AM_PCI_DISP or o.address_mode in PC_INDEX):
                g = gap_of(a + 2 + o.mem.disp)
                if g:
                    low, high = min(low, g[0] & ~0xf), max(high, g[1])
    high = (high + 15) & ~15
    if any(low <= t < high for t in below):
        raise SystemExit('a target below the floor lies in the copied span')
    return dict(low=low, high=high, patches=patches, hazards=hazards, unsafe=unsafe, below=sorted(below),
                safe=sorted(safe), entries=len(entries), targets=targets,
                code=sum(h2[a].size for a in spans), instructions=len(h2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', default=str(ROOT/'tmp/slave/include/e2.i'))
    parser.add_argument('--report')
    args = parser.parse_args()
    r = analyse()
    out = Path(args.out).resolve()
    if not out.is_relative_to(ROOT/'tmp'):
        raise ValueError('output must stay in project tmp/')
    lines = ['; Generated by tools/e2_tables.py from the pinned f1gp; never commit this file.',
             f'E2_LOW = ${r["low"]:x}', f'E2_HIGH = ${r["high"]:x}',
             f'E2_PATCHES = {len(r["patches"])}', 'e2_patches']
    # Bit 31: the operand is in hunk 2 (patched in the chip original and in the copy).
    lines += [f'        dc.l ${(h == 2) << 31 | at:x}' for h, at in r['patches']]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines)+'\n')
    summary = dict(span=[f'h2+{r["low"]:x}', f'h2+{r["high"]:x}'], copied_bytes=r['high']-r['low'],
                   closure_code_bytes=r['code'], h2_instructions=r['instructions'],
                   entries=r['entries'], safe_entries=len(r['safe']), below_floor=len(r['below']),
                   patches=len(r['patches']),
                   patches_h0=sum(h == 0 for h, _ in r['patches']),
                   hazards={f'h2+{a:x}': v for a, v in sorted(r['hazards'].items())},
                   unsafe_entries={f'h2+{e:x}': v for e, v in sorted(r['unsafe'].items())},
                   slave_targets=len(r['targets']))
    if args.report:
        path = Path(args.report).resolve()
        if not path.is_relative_to(ROOT/'tmp'):
            raise ValueError('report must stay in project tmp/')
        path.write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('unsafe_entries',)}, indent=2))


if __name__ == '__main__':
    main()
