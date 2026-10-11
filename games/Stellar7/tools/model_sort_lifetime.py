#!/usr/bin/env python3
"""Check observed native model-sort scratch reads follow initialization.

Only complete observed model passes are covered. This does not prove static
array capacity, unseen callers, or all render-to-simulation dependencies.
"""
import argparse
import json
import re
from pathlib import Path
import barto

GUARDS = {0x13978:'4e55ffec', 0x139d4:'2948df4c',
          0x13a0e:'21acdf447800', 0x13a84:'21807800',
          0x13ad6:'2213', 0x13adc:'b2b00800', 0x13b00:'24301800',
          0x13b12:'23b038001800', 0x13b1c:'21823800',
          0x13b24:'29701800df44', 0x13b32:'23b038001800',
          0x13b3c:'21acdf443800', 0x13be8:'2953df44',
          0x13cc4:'4cdf08f4'}


def inspect(folder):
    folder = Path(folder)
    meta = {k:int(v,0) for k,v in re.findall(r'^(code|data|base)=(\S+)',
                                            (folder/'anchor.txt').read_text(), re.M)}
    memory = (folder/'code.bin').read_bytes()
    for pc, expected in GUARDS.items():
        expected = bytes.fromhex(expected)
        at = meta['code']-meta['base']+pc
        assert memory[at:at+len(expected)] == expected, hex(pc)
    active = None
    passes = []
    incomplete_prefix_reads = 0
    for field in (trace := barto.load(folder/'trace.bin')).fields:
        for pc, cost, regs in trace.instructions(field):
            if pc is None:
                continue
            pc -= meta['code']
            if pc == 0x13978:
                assert active is None, 'overlapping model passes'
                active = dict(keys=set(), pointers=set(), key_reads=0, pointer_reads=0,
                              key_writes=0, pointer_writes=0, field=field.index)
            if pc not in GUARDS or pc == 0x13978:
                continue
            if active is None:
                if pc == 0x13be8:
                    incomplete_prefix_reads += 1
                continue

            def slot(value):
                assert value >= 0 and value % 4 == 0, 'misaligned/negative model-sort index'
                return value//4

            def read(kind, index):
                assert index in active[kind], f'{kind} slot {index} read before initialization'
                active['key_reads' if kind == 'keys' else 'pointer_reads'] += 1

            def write(kind, index):
                active[kind].add(index)
                active['key_writes' if kind == 'keys' else 'pointer_writes'] += 1

            if pc == 0x139d4:
                write('pointers', 0)
            elif pc == 0x13a0e:
                write('pointers', slot(regs[7]))
            elif pc == 0x13a84:
                write('keys', slot(regs[7]))
            elif pc == 0x13ad6:
                read('keys', slot(regs[11]-meta['data']-0x5e68))
            elif pc == 0x13adc:
                read('keys', slot(regs[0]))
            elif pc == 0x13b00:
                read('keys', slot(regs[1]))
            elif pc == 0x13b12:
                read('keys', slot(regs[3])); write('keys', slot(regs[1]))
            elif pc == 0x13b1c:
                write('keys', slot(regs[3]))
            elif pc == 0x13b24:
                read('pointers', slot(regs[1]))
            elif pc == 0x13b32:
                read('pointers', slot(regs[3])); write('pointers', slot(regs[1]))
            elif pc == 0x13b3c:
                write('pointers', slot(regs[3]))
            elif pc == 0x13be8:
                read('pointers', slot(regs[11]-meta['data']-0x5f4c))
            elif pc == 0x13cc4:
                active['keys'] = sorted(active['keys'])
                active['pointers'] = sorted(active['pointers'])
                passes.append(active); active = None
    assert passes, 'no complete observed model passes'
    return dict(passes=passes, incomplete_prefix_reads=incomplete_prefix_reads,
                incomplete_pass_at_end=active is not None,
                scope='Guarded native instructions in this trace only; indexed reads follow writes within each observed model pass. No static capacity or unseen-path proof.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.capture), indent=2))
