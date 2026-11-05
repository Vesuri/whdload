#!/usr/bin/env python3
"""Exact PC-range instruction costs for verified leaf c2p/limiter routines on covered 020/030 cores."""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path
import capstone
from matrix_report import report, read_aprof
from reconstruct import ROOT, SLAVE_SHA

LEAVES = [('tod_limiter', 0x17b8, 0x17ee), ('c2p_128', 0x17f6, 0x195e),
          ('c2p_166', 0x195e, 0x1ac6), ('c2p_200', 0x1ac6, 0x1c2e)]


def verify_leaves():
    original = (ROOT/'tmp/game/WingCommanderCD32/WingCommanderCD32.Slave').read_bytes()
    if hashlib.sha256(original).hexdigest() != SLAVE_SHA:
        raise ValueError('changed original slave')
    code = original[32:-4]
    decoder = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_M68K_020)
    for name, start, end in LEAVES:
        instructions = list(decoder.disasm(code[start:end], start))
        if sum(i.size for i in instructions) != end-start or instructions[-1].mnemonic != 'rts':
            raise ValueError('incomplete leaf boundary: '+name)
        for instruction in instructions:
            op = instruction.mnemonic.split('.')[0]
            if op in ('jsr', 'bsr', 'jmp', 'trap', 'trapv', 'rte', 'rtd', 'rtr', 'stop', 'reset', 'bkpt', 'illegal'):
                raise ValueError('non-leaf control flow: '+name)
            if op.startswith('db') or (op.startswith('b') and op not in ('btst', 'bset', 'bclr', 'bchg')):
                match = re.search(r'\$([0-9a-f]+)$', instruction.op_str)
                if not match or not start <= int(match[1], 16) < end:
                    raise ValueError('branch leaves routine: '+name)
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    original_code = verify_leaves()
    base = json.loads((args.run/'result.json').read_text())
    if base['machine'] not in ('a1200-fast','a1200-030'):
        raise ValueError('only covered 020/030 cores are supported')
    memory = (args.run/'fast.bin').read_bytes()
    for name, start, end in LEAVES:
        at = base['slave']-0x200000
        if memory[at+start:at+end] != original_code[start:end]:
            raise ValueError('live leaf differs from verified source: '+name)
    summary = report(args.run)
    calls = collections.Counter()
    for line in (args.run/'matrix-events.txt').read_text().splitlines():
        fields = line.split()
        if fields[0] == 'C':
            calls[(int(fields[1]), int(fields[4])//320)] += 1
    scenes = []
    for index, scene in enumerate(summary['scenes']):
        if index == 0:
            continue  # Slave address range is not established throughout reset/loading.
        header, pcs, _, _, residual = read_aprof(args.run/f'scene-{index:02d}.aprof')
        if header.get('source_pc_stable') != 1:
            raise ValueError('stable executing-PC accounting required')
        by_pc = {p[0]: p for p in pcs}
        leaves = []
        for name, start, end in LEAVES:
            start += base['slave']; end += base['slave']
            units = sum(row[1] for pc, row in by_pc.items() if start <= pc < end)
            entries = by_pc.get(start, [0, 0, 0])[2]
            expected = sum(calls[(index, n)] for n in (128, 166, 200)) if name == 'tod_limiter' else calls[(index, int(name[4:]))]
            if entries != expected:
                raise ValueError(f'leaf entry/census disagreement: {scene["scene"]} {name}')
            leaves.append(dict(name=name, entries=entries, instruction_units=units,
                               instruction_share=units/header['units']))
        scenes.append(dict(scene=scene['scene'], seconds=scene['seconds'], publications=scene['publications'],
                           publication_hz=scene['publication_hz'], leaves=leaves))
    print(json.dumps(dict(leaf_boundaries_verified=True, scenes=scenes,
                         scope='Instruction-body costs in verified call-free routines, including instruction memory stalls. '
                               'No calling-context attribution is used. Interrupt service and between-instruction gaps are excluded. '
                               'These are not entry-to-return elapsed-time costs or a complete phase 4 baseline.'), indent=2))


if __name__ == '__main__':
    main()
