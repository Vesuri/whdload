#!/usr/bin/env python3
"""Build src/relocs.i: how the Enhanced slave relocates its copy of the program.

    python3 tools/relocs.py            write src/relocs.i and print the summary
    python3 tools/relocs.py --check    only check that src/relocs.i is up to date
    python3 tools/relocs.py --codebits FILE   the VERIFY build's chip trap map (game.sh)

The slave copies chip $5000-$13000 (COPY) to the ExpMem after the decryption and its patches,
then adds the copy's offset to the 32-bit fields listed here. Only addresses go into the file,
no game bytes. From tools/codemap.py's reached code:

- _rel_code: the operand of every jsr/jmp abs.l into the copied code, the immediate of every
  move.l #CODE,SLOT into a pointer slot (codemap.POINTER_SLOTS), and the entries of the jump
  table at $C5D6 (read PC-relative, so the copy's own table is read).
- _rel_moved: absolute operands of the variables that moved into the copy, because the code
  also reads them PC-relative (MOVED): the key byte $C526 and the horizon plotter's colour
  cache $CA4E. A whole-image scan must find no other occurrence of their address.
- _rel_smc: the horizon plotter's writes into its own instructions ($CA86-$CAA4), so the copy
  writes its own slots (the slave then replaces the plotter's loops, which removes the reads).
- _rel_tab: the base operands of read-only tables inside the copy (TABLES), so their readers
  read the copy: lea abs.l,An, movea.l #imm,An and abs.l reads. Readers left out (a table
  address reaching a register another way) still read chip, where the bytes are the same.
- WIN, the window of read-only tables above the program, is not copied: its base operands
  (lea, movea.l #imm) are found and counted in the summary but stay chip addresses. Copying
  it (72 KB) gained nothing measurable once the display fetches 64 bits wide, and without it
  the ExpMem fits beside WHDLoad on a 1 MB A500.
- _tramp: chip routine entries (codemap's pointer-reached entries and subroutine entries)
  whose address is held in data (handler tables) or in code that is not copied: each gets
  `jmp copy` over its first 6 bytes, if those are all instruction bytes and no branch or
  other entry lands inside them.

Everything else stays as it is: data operands keep their chip addresses, relative branches
stay inside the copy, and code the analysis does not reach runs from chip, unrelocated (the
chip program is left intact apart from the trampolines). The script stops on what it cannot
place: a branch out of the copy, an abs.w code reference, a PC-relative read of a variable not
in MOVED or of a table not in TABLES.
"""
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import codemap as C  # noqa: E402
from capstone import m68k as M  # noqa: E402

COPY = (0x5000, 0x13000)
OUT = ROOT / 'src/relocs.i'
# PC-relative data reads and what they read. 'moved': a variable written elsewhere through its
# absolute address, so it moves into the copy. ('table', n): n long entries of a read-only table;
# entries that are code addresses are relocated. 'const': a read-only table of constants.
PCREL = {
    0xC526: 'moved',             # key byte, written by the level-3 handler at $C4E4
    0xCA4E: 'moved',             # horizon plotter colour cache, written at $CA72
    0xC5D6: ('table', 18),       # jump table of $C5CC: movea.l $C5D6(pc,d4.w),a0 / jmp (a0)
    0xE408: 'const',             # bit masks read by $E402 (and by $F930's routine through a4)
}
# Absolute operands into code bytes that are data: lea $9272,a0 at $9278 is the end of the
# high-score table $91E2-$9271, which the following instruction happens to start at.
DATA_NOT_CODE = {0x9278}
# The stack: movea.l #$7FFFE,a7 at the entry. The slave puts its fast stack's top there.
STACK_OPERAND = 0xD7E4
# Slave patches applied before the copy: their bytes are copied as patched and must hold no
# relocation (the original instructions there have none either).
PATCHED = [(0x94C6, 0x94CC), (0xC4D2, 0xC4D8)]
# Read-only tables inside the copy (no write in the data-flow scans of the benchmark, the demo
# and the a500, no absolute write in the code): chip address range, what.
TABLES = [
    (0xD1B0, 0xD29C, 'the model pointers of $BB22 and $BFB8 (the models stay in chip: the '
                     'blitter reads parts of them)'),
    (0xE408, 0xE428, 'bit masks ($E402 reads them PC-relative, $F930 through a4)'),
    (0x11EEA, 0x12300, 'the horizon plotter\'s plane patterns (lea $11EEA,a3 at $CA5E)'),
    (0x12700, 0x13000, 'tables'),
]
# The window above the program: the transform's and the collision tests' log, exp and angle
# tables (movea.l #$59FFE,a6 / #$5DFFE,a5 / #$5D400,a3, indexed by signed words, so
# $55400-$65FFD), and the star tables $5D8FE and $5DB4E.
WIN = (0x54000, 0x66000)
# $D592 and $D5E0 fill the star tables from the RNG at the entry, $D802 and $D80A then patch
# two bytes; the slave copies the window after $D5E0 (_wsync, called from the copy's $D812).
GENERATORS = {0xD592, 0xD5E0}
WIN_WRITES = {0xD802, 0xD80A}
WIN_SYNC = 0xD812           # jsr $D5E0.l in the entry
# Left in chip: move.l #$59ADD,$11E00 at $D9FA (a pointer kept in a variable) and the level
# start's lea $60000,a0 at $D53E (it adds the level x $1000, past the window).
WIN_LEFT = {0xD9FA, 0xD53E}


def in_copy(a):
    return COPY[0] <= a < COPY[1]


def field_offsets(mem, ins, value):
    """Offsets in the instruction of the 32-bit fields holding VALUE."""
    return [o for o, v in C.ext_words(mem, ins) if v == value]


def analyse():
    code = C.build()
    mem = code.mem
    if code.conflicts or code.bad:
        raise SystemExit(f'code map: overlaps {sorted(code.conflicts)[:5]}, undecodable {sorted(code.bad)[:5]}')
    rel_code, rel_moved, rel_smc, problems = [], [], [], []
    rel_tab, rel_win = [], []
    branch_targets, calls = set(), set()
    code_ptr_values = set()      # code addresses that relocated fields hold
    for a in sorted(code.insns):
        ins = code.insns[a]
        if not in_copy(a):
            continue
        m = ins.mnemonic
        t = C.branch_target(ins)
        if t is not None:
            branch_targets.add(t)
            if m.startswith('bsr'):
                calls.add(t)
            if not in_copy(t):
                problems.append(f'${a:05x} {m} {ins.op_str}: branch out of the copy')
        slot = C.pointer_store(ins)
        for op in ins.operands:
            if op.type == M.M68K_OP_MEM and op.address_mode == M.M68K_AM_ABSOLUTE_DATA_SHORT:
                v = op.imm & 0xffff
                if code.is_code(v):
                    problems.append(f'${a:05x} {m} {ins.op_str}: abs.w code reference')
            if op.type == M.M68K_OP_MEM and op.address_mode == M.M68K_AM_ABSOLUTE_DATA_LONG:
                v = op.imm & 0xffffffff
                offs = field_offsets(mem, ins, v)
                if m in ('jsr', 'jmp'):
                    if m == 'jsr':
                        calls.add(v)
                    if in_copy(v) and code.is_code(v):
                        rel_code += [a + o for o in offs]
                        code_ptr_values.add(v)
                        branch_targets.add(v)
                elif PCREL.get(v) == 'moved':
                    rel_moved += [a + o for o in offs]
                elif code.is_code(v) and a not in DATA_NOT_CODE:
                    if 0xCA86 <= a <= 0xCAA4:
                        rel_smc += [a + o for o in offs]
                    else:
                        problems.append(f'${a:05x} {m} {ins.op_str}: absolute access to code bytes')
        if slot is not None and in_copy(slot[0]):
            offs = field_offsets(mem, ins, slot[0])
            rel_code.append(a + offs[0])
            code_ptr_values.add(slot[0])
        tables(mem, ins, rel_tab, rel_win, problems)
        pr = C.pc_rel(ins)
        if pr and m not in ('jsr', 'jmp', 'lea', 'pea'):
            tgt = pr[0]
            if not code.is_code(tgt) and tgt not in PCREL:
                problems.append(f'${a:05x} {m} {ins.op_str}: PC-relative read of ${tgt:05x}, not in PCREL')
        if m == 'jmp' and pr and pr[1] == 'index':
            pass        # computed jumps into branch tables stay inside the copy
    # the jump table entries
    for base, kind in PCREL.items():
        if isinstance(kind, tuple) and kind[0] == 'table':
            for i in range(kind[1]):
                p = base + 4 * i
                v = struct.unpack_from('>I', mem, p)[0]
                if code.is_code(v):
                    rel_code.append(p)
    # moved variables: their address may occur nowhere else in the image
    for v, kind in PCREL.items():
        if kind != 'moved':
            continue
        occ = [p for p in range(0, len(mem) - 3, 2) if struct.unpack_from('>I', mem, p)[0] == v]
        stray = [p for p in occ if p not in rel_moved]
        if stray:
            problems.append(f'moved ${v:05x}: also at {[hex(p) for p in stray]}')
    if mem[WIN_SYNC:WIN_SYNC + 6] != bytes.fromhex('4eb90000d5e0'):
        problems.append(f'${WIN_SYNC:05x} is not jsr $D5E0.l')
    for lo, hi in PATCHED:
        for f in rel_code + rel_moved + rel_smc + rel_tab + rel_win:
            if lo <= f + 3 and f < hi:
                problems.append(f'relocation ${f:05x} inside the slave patch ${lo:05x}-${hi:05x}')
    # trampolines: code addresses held as data anywhere outside the relocated fields and the
    # copied instructions' own operands
    insn_bytes = code.covered
    relocated = set()
    for f in rel_code + rel_moved + rel_smc + rel_tab + rel_win + [STACK_OPERAND]:
        relocated.update(range(f, f + 4))
    tramp, skipped = [], []
    starts = set(code.insns)
    held = set()
    for p in range(0, len(mem) - 3, 2):
        v = struct.unpack_from('>I', mem, p)[0]
        if v in starts and in_copy(v) and p not in relocated:
            if p in insn_bytes and in_copy(p):
                continue        # an operand of copied code: relocated above, or a data address
            held.add(v)
    # Only routine entries: the entries codemap knows are reached through pointers, and
    # subroutine entries. A data word that equals some other instruction's address is a
    # coincidence, not a pointer.
    cand = sorted((held & (set(C.SEEDS) | calls)) | {C.ENTRY})
    for T in cand:
        inside = [x for x in branch_targets | set(cand) if T < x < T + 6]
        notcode = [x for x in range(T, T + 6) if x not in insn_bytes]
        if notcode:
            skipped.append((T, [notcode[0]], 'data'))
        elif inside:
            skipped.append((T, inside, 'entry'))
        else:
            tramp.append(T)
    return dict(code=code, rel_code=sorted(set(rel_code)), rel_moved=sorted(set(rel_moved)),
                rel_smc=sorted(set(rel_smc)), rel_tab=sorted(set(rel_tab)),
                rel_win=sorted(set(rel_win)), tramp=tramp, skipped=skipped, problems=problems)


def tables(mem, ins, rel_tab, rel_win, problems):
    """Classify the instruction's 32-bit operands into TABLES and WIN."""
    a, m, ops = ins.address, ins.mnemonic, ins.operands
    for i, op in enumerate(ops):
        if op.type == M.M68K_OP_MEM and op.address_mode == M.M68K_AM_ABSOLUTE_DATA_LONG:
            kind = 'abs'
        elif op.type == M.M68K_OP_IMM and ins.size >= 6 and m.endswith('.l'):
            kind = 'imm'
        else:
            continue
        v = op.imm & 0xffffffff
        tab = any(lo <= v < hi for lo, hi, _ in TABLES)
        win = WIN[0] <= v < WIN[1]
        if not (tab or win):
            continue
        to_areg = len(ops) == 2 and ops[1].type == M.M68K_OP_REG and \
            M.M68K_REG_A0 <= ops[1].reg <= M.M68K_REG_A7
        base = (m in ('lea', 'lea.l') and kind == 'abs') or (m == 'movea.l' and kind == 'imm' and to_areg)
        read = kind == 'abs' and i == 0 and len(ops) == 2 and m.startswith('move') and \
            ops[1].type == M.M68K_OP_REG
        where = f'${a:05x} {m} {ins.op_str}'
        if win and (a in GENERATORS or a in WIN_WRITES or a in WIN_LEFT):
            continue
        if not (base or (tab and read)):
            problems.append(f'{where}: a table address used other than as a base or a read')
            continue
        offs = field_offsets(mem, ins, v)
        (rel_tab if tab else rel_win).extend(a + o for o in offs[:1])


def crc16(data):
    """resload_CRC16 (CRC-16/ARC: polynomial $8005 reflected, initial 0)."""
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def render(r):
    mem = r['code'].mem
    lines = ['; Generated by tools/relocs.py from disk.1 (SPS 0651): chip addresses of the program',
             '; copy\'s relocations (src/EncounterHD.s _enhance), no game bytes. Do not edit.',
             f'COPY_LO\t\t= ${COPY[0]:x}',
             f'COPY_HI\t\t= ${COPY[1]:x}',
             f'COPY_CRC\t= ${crc16(mem[COPY[0]:COPY[1]]):04x}\t;resload_CRC16 of the copied range after the decryption',
             f'STACK_OPERAND\t= ${STACK_OPERAND:x}\t;movea.l #$7FFFE,a7 at the entry',
             '']

    def table(label, comment, items):
        lines.append(f'; {comment}')
        lines.append(label)
        for i in range(0, len(items), 8):
            lines.append('\tdc.l\t' + ','.join(f'${x:x}' for x in items[i:i + 8]))
        lines.append('\tdc.l\t0')
        lines.append('')
    table('_rel_code', f'{len(r["rel_code"])} code addresses (jsr/jmp abs.l, pointer stores, the $C5D6 table)', r['rel_code'])
    table('_rel_moved', f'{len(r["rel_moved"])} operands of the variables in the copy ($C526, $CA4E)', r['rel_moved'])
    table('_rel_smc', f'{len(r["rel_smc"])} horizon plotter slot writes', r['rel_smc'])
    table('_rel_tab', f'{len(r["rel_tab"])} base operands of the read-only tables in the copy', r['rel_tab'])
    table('_tramp', f'{len(r["tramp"])} chip entries reached through data: jmp to the copy', r['tramp'])
    return '\n'.join(lines)


# VERIFY's chip trap leaves the audio samples alone: the level-3 handler at $804E shares a
# page with the end of the sample at $7004, and $8200-$82FF plays as well.
AUDIO = [(0x7000, 0x8100), (0x8200, 0x8300)]


def codebits(r, path):
    """The VERIFY build's codebits.i: a bit per word of the copied range, MSB first, set at
    each reached instruction's first word, except inside the trampolines and the audio."""
    keep = set()
    for T in r['tramp']:
        keep.update(range(T, T + 6))
    bits = bytearray((COPY[1] - COPY[0]) // 16)
    n = 0
    for a in r['code'].insns:
        if not in_copy(a) or a in keep or any(lo <= a < hi for lo, hi in AUDIO):
            continue
        i = (a - COPY[0]) // 2
        bits[i // 8] |= 0x80 >> (i % 8)
        n += 1
    lines = [f'; tools/relocs.py --codebits: {n} reached instructions of disk.1 to trap in chip (VERIFY)',
             '_codebits']
    for i in range(0, len(bits), 32):
        lines.append('\tdc.b\t' + ','.join(f'${b:02x}' for b in bits[i:i + 32]))
    Path(path).write_text('\n'.join(lines) + '\n')


def main(argv):
    r = analyse()
    if argv[:1] == ['--codebits']:
        codebits(r, argv[1])
        return
    print(f'code: {len(r["code"].insns)} instructions; relocations: code {len(r["rel_code"])}, '
          f'moved {len(r["rel_moved"])}, plotter slots {len(r["rel_smc"])}, tables {len(r["rel_tab"])}, '
          f'window {len(r["rel_win"])}; trampolines {len(r["tramp"])}')
    for T, inside, why in r['skipped']:
        what = 'not code from' if why == 'data' else 'an entry at'
        print(f'  no trampoline at ${T:05x}: {what} {", ".join(f"${x:05x}" for x in inside)}')
    for p in r['problems']:
        print('PROBLEM', p)
    if r['problems']:
        sys.exit(1)
    text = render(r)
    if argv == ['--check']:
        if OUT.read_text() != text:
            sys.exit(f'{OUT.relative_to(ROOT)} is out of date: run tools/relocs.py')
        print('up to date')
        return
    OUT.write_text(text)
    print(f'wrote {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main(sys.argv[1:])
