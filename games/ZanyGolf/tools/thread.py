#!/usr/bin/env python3
"""List Zany Golf's threaded code as 65xx-style instructions.

    python3 tools/thread.py START [END]     FILE1 offsets in hex (END defaults to START+$80)

Each threaded instruction is the 16-bit address of a primitive in FILE1 ($0100-$0c2a)
followed by its operand words; the primitive takes them with (a5)+ and ends with the
dispatch `move.w (a5)+,d5; movea.l d5,a0; jmp (a0)` (internals.md, "The program"). The
primitives are disassembled with m68k-amiga-elf-objdump from tmp/game/<GAME_DIR> and walked
to the dispatch to count their operands. Named ones print as mnemonics; the rest print as
Pxxxx with their 68000 body. A word that is not a primitive prints as `.w` (data, or a
native routine's thread entry). Branch targets and absolute operands are FILE1 offsets;
`#` operands are immediates.
"""
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIMS = (0x100, 0xc2a)

# Primitive address -> mnemonic, for those read so far. d0 is A, d1 X, d2 Y, d4 the N/Z
# result, d3's top bit the carry; addresses are in the a4 bank.
NAMES = {
    0x140: 'NOP', 0x1da: 'ASL A', 0x1e6: 'ORA', 0x1f4: 'ASL', 0x222: 'CLC', 0x358: 'SEC',
    0x3ee: 'EOR #', 0x438: 'JMP', 0x440: 'JMP (,X)', 0x484: 'BCS', 0x492: 'BEQ', 0x4a0: 'BNE',
    0x4ae: 'BPL', 0x4bc: 'BMI', 0x4ca: 'EOR', 0x5e8: 'JSR', 0x602: 'RTS', 0x63c: 'ADC',
    0x726: 'TXA', 0x744: 'TAX', 0x76e: 'STA', 0x7ca: 'STA ,X', 0x7d8: 'STZ', 0x7f2: 'LDY #',
    0x822: 'LDA [],Y', 0x864: 'LDX #', 0x872: 'LDA #', 0x88e: 'LDA', 0x89c: 'LDX',
    0x8aa: 'LDA (),Y', 0x8dc: 'LDY ,X', 0x8ec: 'LDA ,X', 0x9ac: 'DEC A', 0x9b6: 'CMP #',
    0xaf2: 'SBC', 0xb0a: 'INC',
    0xba6: 'MOVW',   # copy the 16-bit word at the first operand to the second
    0xbc0: 'STW #',  # store the second operand's two bytes, as they are, at the first
    0xbea: 'MOVL',   # copy four bytes from the first operand to the second
}
BRANCHES = {0x438, 0x484, 0x492, 0x4a0, 0x4ae, 0x4bc, 0x5e8}
DISPATCH = ['move.w (a5)+,d5', 'movea.l d5,a0', 'jmp (a0)']


def game_dir():
    conf = (ROOT / 'game.conf').read_text()
    return re.search(r'^GAME_DIR=(\S+)', conf, re.M).group(1)


def primitives(path):
    out = subprocess.run(['m68k-amiga-elf-objdump', '-D', '-b', 'binary', '-m', 'm68k:68000',
                          f'--start-address={PRIMS[0]:#x}', f'--stop-address={PRIMS[1]:#x}',
                          str(path)], capture_output=True, text=True, check=True).stdout
    lines = {}
    for line in out.splitlines():
        m = re.match(r'\s*([0-9a-f]+):\s+((?:[0-9a-f]{4} )+)\s*(.*)', line)
        if m:
            lines[int(m.group(1), 16)] = (len(m.group(2).split()) * 2, m.group(3).strip())
    return lines


def walk(lines, pc):
    """(operand words, body) of the primitive at pc: straight on to the dispatch, following
    unconditional branches."""
    n, body, a = 0, [], pc
    for _ in range(80):
        if a not in lines:
            break
        size, text = lines[a]
        if [lines.get(a + o, (0, ''))[1] for o in (0, 2, 4)] == DISPATCH:
            return n, body
        if text.startswith('jmp 290(a4)'):           # into the dispatcher
            return n, body
        if '(a5)+' in text or text == 'addq.w #2,a5':
            n += 1
        body.append(text)
        m = re.match(r'bra[.sw]* 0x([0-9a-f]+)$', text)
        a = int(m.group(1), 16) if m else a + size
    return n, body + ['?']


def main(argv):
    data = (ROOT / 'tmp/game' / game_dir() / 'data/files/FILE1').read_bytes()
    lines = primitives(ROOT / 'tmp/game' / game_dir() / 'data/files/FILE1')
    pc = int(argv[0], 16)
    end = int(argv[1], 16) if len(argv) > 1 else pc + 0x80
    while pc < end:
        w = struct.unpack_from('>H', data, pc)[0]
        if not (PRIMS[0] <= w < PRIMS[1] and w in lines):
            print(f'{pc:04x}: .w      ${w:04x}')
            pc += 2
            continue
        n, body = walk(lines, w)
        if w in BRANCHES:
            n = 1
        ops = [struct.unpack_from('>H', data, pc + 2 + 2 * i)[0] for i in range(n)]
        name = NAMES.get(w, f'P{w:04x}')
        note = '' if w in NAMES else '    ; ' + '; '.join(
            b for b in body if b not in ('move.w (a5)+,d5', 'movea.l d5,a0'))
        print(f'{pc:04x}: {name:8} ' + ' '.join(f'${o:04x}' for o in ops) + note)
        pc += 2 + 2 * n


if __name__ == '__main__':
    main(sys.argv[1:])
