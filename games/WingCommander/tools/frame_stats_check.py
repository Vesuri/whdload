#!/usr/bin/env python3
"""Native frame recorder race/register checks; no performance claims."""
import argparse
import ctypes as C
import json
import re
import struct
from pathlib import Path
from c2p_check import CPU, BASE, STACK, STOP, ck, u, P, I, Q
from cd32_runtime import ROOT


def check(blob, symbols, model, samples, expected):
    c = CPU(blob, model)
    ck(u.uc_mem_map(c.h, 0xdff000, 4096, 7))
    for name, value, fmt in (('timing_active', 1, '>H'),
                             ('timing_data', 0x40000, '>I'),
                             ('frame_stats_buffer', 0xa0000, '>I'),
                             ('frame_stats_started', 1, '>H')):
        c.write(BASE+symbols[name], struct.pack(fmt, value))
    c.write(0x47f02, struct.pack('>I', 300))
    reads = []
    def read_hook(handle, kind, address, size, value, data):
        if address == 0xdff004:
            sample = samples[min(len(reads), len(samples)-1)]
            c.write(address, struct.pack('>I', sample << 8))
            reads.append(sample)
    hook = C.CFUNCTYPE(None, P, I, Q, I, C.c_int64, P)(read_hook)
    handle = C.c_size_t()
    ck(u.uc_hook_add(c.h, C.byref(handle), 1 << 10, hook, None, 0xdff004, 0xdff007))
    for r in range(1, 17):
        c.reg(r, 0x12340000+r)
    c.reg(8, STACK)
    c.reg(17, 0x2715)
    c.write(STACK, struct.pack('>IH', STOP, 4))
    before = [c.reg(r) for r in range(1, 18)]
    ck(u.uc_emu_start(c.h, BASE+symbols['frame_stat'], STOP, 1000000, 10000))
    assert c.reg(18) == STOP
    after = [c.reg(r) for r in range(1, 18)]
    assert before[:7]+before[8:] == after[:7]+after[8:]
    assert after[7] == STACK+4
    assert c.read(BASE+symbols['frame_stats_count'], 4) == struct.pack('>I', 1)
    assert c.read(0xa0010, 4) == struct.pack('>I', (4 << 27) | (300 << 9) | expected)
    c.close()
    return len(reads)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or (ROOT/'tmp').resolve() not in a.output.resolve().parents:
        raise ValueError('new tmp output required')
    blob = (a.build/'payload.bin').read_bytes()
    symbols = {n: int(o, 16) for o, n in re.findall(r'^([0-9A-F]{8}) (\S+)$', (a.build/'slave.lst').read_text(), re.M)}
    # Diagnostic accounting must not alter the game allocator's RAM budget.
    for model in (2,4):
        c=CPU(blob,model)
        c.write(4,struct.pack('>I',0x2000))
        c.write(0x2000-198,bytes.fromhex('23c00003000023c100030004203c000a00004e75'))
        c.write(STACK,struct.pack('>I',STOP));c.reg(8,STACK)
        ck(u.uc_emu_start(c.h,BASE+symbols['frame_stats_init'],STOP,1000000,1000))
        assert c.reg(18)==STOP
        assert c.read(0x30000,8)==struct.pack('>II',16+symbols['FS_RECORDS']*4+(16+2047*(32 if 'release_predict' in symbols else 16) if 'release_pending' in symbols else 0),0x10005)
        c.close()
    cases = []
    for model in (2, 4):
        for samples, expected in (([120, 120], 120), ([0, 256, 256, 256], 256), ([511, 255, 255, 255], 255)):
            reads = check(blob, symbols, model, samples, expected)
            assert reads == len(samples)
            cases.append(dict(model=model, samples=samples, recorded=expected))
    # Removing the second independent bus read must expose the torn timestamp.
    broken = bytearray(blob)
    at = blob.index(bytes.fromhex('263900dff004'), symbols['frame_stat'])
    broken[at:at+6] = bytes.fromhex('26004e714e71')  # move.l d0,d3; nop; nop
    try:
        check(bytes(broken), symbols, 4, [0, 256, 256, 256], 256)
    except AssertionError:
        pass
    else:
        raise AssertionError('torn-read negative control passed')
    a.output.write_text(json.dumps(dict(cases=cases, torn_read_rejected=True), indent=2)+'\n')
    print('PASS: six recorder race/register cases and torn-read negative control')


if __name__ == '__main__':
    main()
