#!/usr/bin/env python3
"""Execute the public OCS slave's TrainSim enemy details conversion dispatch.

While modal_info_changed is set, ocs_info_word/long convert through the C6
changed-block adapter (src/ocs_changed.s); with it clear they drop both
histories and convert the whole image. Every call must give the independent
reference pixels; stores must follow the history. Two mutated slaves (flag
ignored, invalidation dropped) must be rejected. Unicorn is a functional
instrument, never a performance measurement.
"""
import argparse
import hashlib
import json
import random
import struct
from pathlib import Path
from c2p_check import CPU, BASE, STACK, STOP, u, ck
from ocs_display_check import reference
from ocs_reconstruct import new_output, require
from runtime_buffers import load

SRC, DST = 0x50000, (0x60000, 0x70000)
FULL = 160*199


def exercise(blob, sy, model, arm):
    c = CPU(blob, model); rng = random.Random(0x1f0); cases = 0
    history = BASE+sy['ocs_changed_history']; meta = BASE+sy['ocs_changed_meta']; flag = BASE+sy['modal_info_changed']
    def call(src, index, on):
        nonlocal cases
        c.write(flag, struct.pack('>H', on)); c.write(SRC, src); c.write(STACK, struct.pack('>I', STOP))
        for r in range(1, 17): c.reg(r, 0x12340000+r)
        c.reg(1, SRC); c.reg(2, DST[index]); c.reg(8, STACK); c.reg(9, 320); c.reg(10, 200)
        before = [c.reg(r) for r in range(1, 17)]
        other = c.read(DST[1-index]-64, 32448); c.writes = []
        ck(u.uc_emu_start(c.h, BASE+sy['ocs_info_'+arm], STOP, 20000000, 6000000))
        require(c.reg(18) == STOP and c.reg(9) == 0, 'conversion failed')
        require(c.reg(8) == STACK+4, 'stack balance')
        require(all(c.reg(r) == before[r-1] for r in range(1, 17) if r not in (8, 9)), 'register preservation')
        packed = reference(src, 320, 200); plane = 40*202; n = 40*199; got = c.read(DST[index], 4*plane)
        require(all(got[p*plane+80:p*plane+80+n] == packed[p*n:(p+1)*n] for p in range(4)), 'pixels differ')
        require(c.read(DST[1-index]-64, 32448) == other, 'opposite destination modified')
        stores = 0
        for address, size in c.writes:
            if DST[index] <= address < DST[index]+4*plane: stores += size
            else: require(STACK-512 <= address < STACK+4 or history <= address < history+128000 or meta <= address < meta+34, 'unowned write')
        cases += 1
        return stores
    try:
        for p in DST: c.write(p-64, b'\xa5'*32448)
        a = bytearray(rng.randbytes(64000)); b = bytes(rng.randbytes(64000))
        for index in (0, 1): require(call(bytes(a), index, 1) == FULL, 'first details pass not full')
        for index in (0, 1): require(call(bytes(a), index, 1) == 0, 'unchanged details pass stored')
        a[32000] ^= 255
        for index in (0, 1): require(call(bytes(a), index, 1) == 16, 'wrong changed extent')
        # A conversion outside the details (flag clear) with other pixels, then
        # the details again with the old ones: the history must not be trusted.
        for index in (0, 1): require(call(b, index, 0) == FULL, 'flag-clear conversion not full')
        for index in (0, 1): require(call(bytes(a), index, 1) == FULL, 'history survived a flag-clear conversion')
        return cases
    finally: c.close()


def mutate(blob, sy, name):
    m = bytearray(blob)
    if name == 'flag_ignored':
        # ocs_info_set always answers "clear".
        m[sy['ocs_info_set']:sy['ocs_info_set']+6] = bytes.fromhex('44fc00044e75')
    else:
        # The flag-clear path keeps the histories.
        for arm in ('word', 'long'):
            for at in range(sy['ocs_info_'+arm], sy['ocs_info_'+arm]+22, 2):
                if m[at:at+2] == b'\x61\x00' and at+2+struct.unpack('>h', m[at+2:at+4])[0] == sy['ocs_changed_invalidate']:
                    m[at:at+4] = bytes.fromhex('4e714e71'); break
            else: raise ValueError('no invalidation call in ocs_info_'+arm)
    return bytes(m)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('build'); p.add_argument('--output', required=True); a = p.parse_args()
    out = new_output(a.output); out.mkdir(parents=True)
    b = json.loads((Path(a.build)/'build.json').read_text()); sy = b['symbols']
    slave = (Path(a.build)/'WingCommander.Slave').read_bytes()
    blob = load(slave)+bytes(b['runtime_workspace_bytes'])
    cases = {f'{model}-{arm}': exercise(blob, sy, model, arm) for model, arm in ((1, 'word'), (2, 'long'))}
    rejected = []
    for name in ('flag_ignored', 'invalidation_dropped'):
        try: exercise(mutate(blob, sy, name), sy, 1, 'word')
        except (ValueError, AssertionError): rejected.append(name)
        else: raise ValueError('mutation escaped: '+name)
    out.joinpath('report.json').write_text(json.dumps(dict(passed=True, cases=cases, rejected=rejected, slave_sha256=hashlib.sha256(slave).hexdigest()), indent=2)+'\n')
    print(sum(cases.values()), 'details conversion cases;', len(rejected), 'mutations rejected')


if __name__ == '__main__': main()
