#!/usr/bin/env python3
"""Verify that the paused capture handshake restored DOS fields and chip scratch."""
import argparse
import os
import re
import struct
from pathlib import Path
from lov_report import regions

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--base', type=lambda s: int(s, 0), default=0xc00000)
a = p.parse_args()
os.environ['SLAVE'] = str(a.capture/'slave.slave')
b = (a.capture/'code.bin').read_bytes()
lst = (a.capture/'slave.lst').read_text(errors='replace')
slave = next(lo for lo, hi, name, off in regions(b, a.base) if name == 'slave')
m = re.search(r'^_profile_state\s+00:([0-9A-F]{8})\s*$', lst, re.M)
assert m, 'missing profiler metadata state'
sr, task, seglist, tasknum, scratch = struct.unpack_from(
    '>HIII32s', b, slave-a.base+int(m[1], 16))
assert sr & 0x2000, 'handshake was not in supervisor context'
assert (a.capture/'profiler-chip.bin').read_bytes() == scratch, 'chip scratch was not restored'
current = (a.capture/'profiler-task.bin').read_bytes()
assert len(current) == 16, 'incomplete DOS metadata snapshot'
assert struct.unpack_from('>I', current, 0)[0] == seglist, 'DOS segment list was not restored'
assert struct.unpack_from('>I', current, 12)[0] == tasknum, 'DOS task number was not restored'
print('profiler handshake: original DOS fields and all 32 chip bytes restored')
