#!/usr/bin/env python3
"""Execute CD32 history setup without consuming the native game allocator."""
import argparse
import json
import re
import struct
from pathlib import Path
from c2p_check import BASE, CPU, STACK, STOP, ck, u


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path)
    a = p.parse_args()
    blob = (a.build/'payload.bin').read_bytes()
    sy = {n: int(o, 16) for o, n in re.findall(
        r'^([0-9A-F]{8}) (\S+)$', (a.build/'slave.lst').read_text(), re.M)}
    start = sy['flight_history_storage']
    assert len(blob) - start == 128000
    results = []
    for model in (2, 4):
        for address, fast in ((BASE, False), (0x300000, True),
                              (0x9e0000, False), (0xc00000, False),
                              (0x1000000, True)):
            c = CPU(blob, model)
            if address != BASE:
                ck(u.uc_mem_map(c.h, address & ~0xfffff, 0x200000, 7))
                c.write(address, blob)
            c.write(4, struct.pack('>I', 0x4000))
            # Neither native allocation nor TypeOfMem may be called: the
            # slave is owned by WHDLoad, outside KickEmu's Exec memory list.
            for offset in (-198, -534):
                c.write(0x4000+offset, bytes.fromhex('4afc'))
            c.write(STACK, struct.pack('>I', STOP))
            c.reg(8, STACK)
            before = [c.reg(r) for r in range(1, 17)]
            ck(u.uc_emu_start(c.h, address+sy['flight_render_init'], STOP, 1000000, 1000))
            assert c.reg(18) == STOP
            expected = address+start if fast else 0xffffffff
            assert c.read(address+sy['flight_history'], 4) == struct.pack('>I', expected)
            after = [c.reg(r) for r in range(1, 17)]
            assert before[:7]+before[8:] == after[:7]+after[8:]
            assert after[7] == STACK+4
            results.append(dict(model=model, slave=address, history=expected))
            c.close()
    print(json.dumps(dict(cases=results, native_allocations=0)))


if __name__ == '__main__':
    main()
