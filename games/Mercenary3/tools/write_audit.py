#!/usr/bin/env python3
"""Which memory does each main-loop call site write? Route coverage from kept traces.

  KEEP_TRACE=1 python3 tools/route_profile.py tmp/prof/audit
  python3 tools/write_audit.py tmp/prof/audit [FIRST_FIELD]

Reads the chunk-*.bin traces in order (from FIRST_FIELD, default 175: gameplay), decodes
every executed game instruction with capstone from the trace's chip snapshot and evaluates
its destination from the recorded registers (after Powerdrome's audit_code_writes.py).
Each write is attributed to the main-loop call site running at the time; interrupt code
(from a level 1..6 autovector target to its RTE, the game's or the slave's) to 'irq'. The display buffers are counted,
not listed. Only executed paths are covered; slave code in fast RAM is not decoded.
"""
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
from capstone.m68k_const import M68K_OP_MEM
from route_profile import CALLS, IMAGE, IMAGE_END, ROOT, label, slave_code

# Main loop call sites before the ticks (chip addresses of the instructions), the tick loop,
# and the inline blocks after it; with CALLS they split a pass into phases.
SITES = {0x5a2e2: 0x5a298, 0x5a2e8: 0x50f3a, 0x5a2ee: None, 0x5a300: 0x4b32a, 0x5a306: 0x59b5c,
         0x5a30a: 0x4d39e, 0x5a310: 0x563b4, 0x5a31a: 0x51f32, 0x5a334: 0x59eca,
         0x5a338: 0x59b94, 0x5a33c: 0x5219a, 0x5a342: 0x548b6, 0x5a34e: 0x4c92c,
         0x5a354: 0x4b2e2, 0x5a35a: None, 0x5a3b0: None, 0x5a3d4: 0x5125e, 0x5a3de: None,
         0x5a40a: None, 0x5a440: None, 0x5a4da: None, **CALLS}
BUFFERS = ((0x68000, 0x70000), (0x78000, 0x80000))
WRITERS = set('move movem movep clr neg negx not add addi addq addx sub subi subq subx and '
              'andi or ori eor eori bchg bclr bset tas asl asr lsl lsr rol ror roxl roxr '
              'abcd sbcd nbcd'.split())
READONLY = set('cmp cmpa cmpi cmpm tst btst muls mulu divs divu chk lea pea jmp jsr'.split())


def ea(op, regs, width):
    mode = op.address_mode
    if mode in (3, 4, 5):
        return (regs[op.reg - 1] - (max(width, 2) if op.reg == 16 else width) * (mode == 5)) & 0xffffffff
    if mode == 6:
        return (regs[op.mem.base_reg - 1] + op.mem.disp) & 0xffffffff
    if mode in (7, 8):
        index = regs[op.mem.index_reg - 1]
        if not op.mem.index_size:
            index = (index & 0x7fff) - (index & 0x8000)
        return (regs[op.mem.base_reg - 1] + op.mem.disp + index * (op.mem.scale or 1)) & 0xffffffff
    if mode == 16:
        return ((op.imm & 0x7fff) - (op.imm & 0x8000)) & 0xffffffff
    if mode == 17:
        return op.imm & 0xffffffff
    raise ValueError(mode)


def ranges(addrs):
    out, start, prev = [], None, None
    for a in sorted(addrs):
        if start is None:
            start = prev = a
        elif a == prev + 1:
            prev = a
        else:
            out.append((start, prev + 1))
            start = prev = a
    if start is not None:
        out.append((start, prev + 1))
    return out


def main():
    d = sys.argv[1]
    first = int(sys.argv[2]) if len(sys.argv) > 2 else 175
    chunks = sorted(f for f in os.listdir(d) if f.startswith('chunk-') and f.endswith('.bin'))
    chunks = [f for f in chunks if int(f[6:11]) >= first]
    md = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
    md.detail = True
    decoded, writes, buffers, unsupported = {}, collections.defaultdict(set), collections.Counter(), collections.Counter()
    # The game's interrupt handlers return through the slave's patched exits (RTE in fast RAM).
    meta = json.load(open(os.path.join(d, 'route.json')))
    sbase, scode = int(meta['slave_base'], 16), slave_code(os.path.join(ROOT, meta['slave']))
    slave_rte = {sbase + o for o in range(0, len(scode) - 1, 2) if scode[o:o + 2] == b'\x4e\x73'}
    phase, irq = 'start', 0
    for name in chunks:
        t = barto.load(os.path.join(d, name))
        # Interrupt handlers: the level 1..6 autovectors in the chip snapshot.
        handlers = {int.from_bytes(t.chip[v:v + 4], 'big') for v in range(0x64, 0x7c, 4)}
        for f in t.fields:
            for pc, _, regs in t.instructions(f):
                if pc is None:
                    continue
                if pc == 0x7fffffff:
                    continue
                if pc in handlers:
                    irq += 1
                if not irq and pc in SITES:
                    phase = pc
                if pc in slave_rte:
                    irq = max(irq - 1, 0)
                if not IMAGE <= pc < IMAGE_END:
                    continue
                ins = decoded.get(pc)
                if ins is None:
                    ins = decoded[pc] = next(md.disasm(t.chip[pc:pc + 22], pc), None)
                    assert ins, f'undecodable executed instruction at {pc:#x}'
                op = ins.mnemonic.split('.')[0]
                if op == 'rte':
                    irq = max(irq - 1, 0)
                    continue
                ops = ins.operands
                if not ops or ops[-1].type != M68K_OP_MEM or op in READONLY:
                    continue
                if op not in WRITERS and not (op.startswith('s') and op not in ('stop', 'swap', 'suba')):
                    unsupported[(pc, ins.mnemonic)] += 1
                    continue
                width = {'b': 1, 'w': 2, 'l': 4}.get(ins.mnemonic[-1], 1)
                if op == 'movem':
                    width *= int.from_bytes(t.chip[pc + 2:pc + 4], 'big').bit_count()
                try:
                    dest = ea(ops[-1], regs, width)
                except ValueError:
                    unsupported[(pc, ins.mnemonic)] += 1
                    continue
                if (len(ops) == 2 and ops[0].type == M68K_OP_MEM and ops[0].address_mode == 5
                        and ops[-1].address_mode == 5 and ops[0].reg == ops[-1].reg):
                    dest -= max(width, 2) if ops[-1].reg == 16 else width
                span = range(dest, dest + 2 * width, 2) if op == 'movep' else range(dest, dest + width)
                key = 'irq' if irq else phase
                for b in span:
                    b &= 0xffffff
                    if any(lo <= b < hi for lo, hi in BUFFERS):
                        buffers[key] += 1
                    else:
                        writes[key].add(b)
        print(f'{name}: {len(decoded)} instructions decoded', file=sys.stderr)
    order = [s for s in SITES if s in writes or s in buffers] + [k for k in ('irq', 'start') if k in writes or k in buffers]
    for key in sorted(order, key=lambda k: (isinstance(k, str), k if isinstance(k, int) else 0)):
        callee = SITES.get(key) if isinstance(key, int) else None
        head = (f'{label(key)} ({key:05x})' if isinstance(key, int) else key) + \
               (f' call {label(callee)} ({callee:05x})' if callee else '')
        rs = ranges(writes.get(key, ()))
        print(f'{head}: {sum(b - a for a, b in rs)} bytes in {len(rs)} ranges, '
              f'{buffers.get(key, 0)} display-buffer byte writes')
        print('   ' + ' '.join(f'{a:05x}' + (f'-{b - 1:05x}' if b - a > 1 else '') for a, b in rs))
    if unsupported:
        print('unhandled:', ', '.join(f'{pc:05x} {m} x{n}' for (pc, m), n in unsupported.most_common(10)))


if __name__ == '__main__':
    main()
