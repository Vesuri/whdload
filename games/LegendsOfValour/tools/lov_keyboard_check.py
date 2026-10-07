#!/usr/bin/env python3
"""Check native input.device → console → historical keyboard collector delivery."""
import argparse
import json
import re
import struct
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--base', type=lambda s: int(s, 0), default=0x200000)
p.add_argument('--slots', type=int, default=512, help='VERIFY queue capacity')
p.add_argument('--require-full', action='store_true', help='require queue backpressure and recovery')
p.add_argument('--ansi', action='store_true', help='also require the native cursor-up console sequence')
p.add_argument('--blocking', action='store_true', help='first byte read by the native blocking entry')
p.add_argument('--compare', type=Path, help='require identical delivery and consumption in another capture')
a = p.parse_args()

def inspect(root):
    metadata = json.loads((root/'ticks/metadata.json').read_text())
    assert metadata.get('complete') and metadata.get('sample_unit') == 'completed tick'
    mem = (root/'ticks/final-code.bin').read_bytes()
    listing = (root/'slave.lst').read_text(errors='replace')
    slave = int(re.search(r'^slave (0x[0-9a-f]+)', (root/'anchor.txt').read_text(), re.M)[1], 16)
    def offset(name):
        return slave + int(re.search(r'^'+name+r'\s+00:([0-9A-F]{8})\s*$', listing, re.M)[1], 16)-a.base
    def value(name, size=4):
        at = offset(name)
        assert 0 <= at <= len(mem)-size
        return int.from_bytes(mem[at:at+size], 'big')
    assert value('_timing_keys_error', 2) == value('_sim_keys_error', 2) == 0
    assert value('_timing_keys_sent') == (9 if a.ansi else 7) and value('_timing_keys_done', 2) == 1
    assert value('_timing_keys_signal') == 0, 'fixture still wakes a task after completion'
    assert value('_sim_keys_live', 2) == value('_sim_keys_pending', 2) == 1
    count = value('_sim_keys_reads')
    assert count in ((6,7) if a.ansi else (4,)), ('unexpected converted console byte count', count)
    records = [struct.unpack_from('>IIHH', mem, offset('_sim_keys_readlog')+12*i) for i in range(count)]
    data = bytes(r[2] for r in records)
    assert data[:4] == b'aBcc', records
    if a.ansi:
        assert data[4:] in (b'\x9bA', b'\x1b[A'), ('not a complete native cursor-up sequence', data)
    if a.blocking:
        assert value('_timing_keys_blocked', 2) == 2 and value('_timing_keys_blocked_byte', 2) == 97
        assert value('_sim_keys_waits') > 0, 'blocking reader never had to wait'
        assert [r[3] for r in records] == [0]+[1]*(count-1)
    else:
        assert all(r[3] == 1 for r in records), 'expected historical gameplay reads'
    assert all(((r[1]-r[0]) & 0xffffffff) < 0x80000000 for r in records if r[3]), 'consumed before timestamp'
    assert value('_sim_keys_head', 2) == value('_sim_keys_tail', 2) == count % a.slots
    if a.require_full:
        assert value('_sim_keys_full_waits') > 0, 'queue never filled'
        assert value('_sim_keys_full', 2) == 0, 'collector still waiting for space'
    print(root.name, f'native console bytes {data!r} delivered exactly once:', records)
    return records

records = inspect(a.capture)
if a.compare:
    assert records == inspect(a.compare), 'rendering load changed keyboard timing/order'
    print('Native console delivery timestamps and consumption fields match under drawing delay')
