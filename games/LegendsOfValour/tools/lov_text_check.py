#!/usr/bin/env python3
"""Check native save-name editing, blocking console reads and resumed world ticks."""
import argparse
import json
import re
import struct
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--base', type=lambda s: int(s, 0), default=0x200000)
a = p.parse_args()
root = a.capture
metadata = json.loads((root/'ticks/metadata.json').read_text())
assert metadata.get('complete') and metadata.get('sample_unit') == 'completed tick'
samples = json.loads((root/'ticks/samples.json').read_text())
mem = (root/'ticks/final-code.bin').read_bytes()
listing = (root/'slave.lst').read_text(errors='replace')
slave = int(re.search(r'^slave (0x[0-9a-f]+)', (root/'anchor.txt').read_text(), re.M)[1], 16)

def read(address, size):
    at = address-a.base
    assert 0 <= at <= len(mem)-size, hex(address)
    return mem[at:at+size]

def symbol(name):
    match = re.search(r'^'+name+r'\s+00:([0-9A-F]{8})\s*$', listing, re.M)
    assert match, name
    return slave+int(match[1], 16)

def value(name, size=4):
    return int.from_bytes(read(symbol(name), size), 'big')

assert value('_timing_keys_text_firstfield') > 0, 'native save panel did not poll'
assert value('_timing_keys_sent') == 11 and value('_timing_keys_done', 2) == 1
assert value('_timing_keys_error', 2) == value('_sim_keys_error', 2) == 0
assert value('_sim_keys_reads') == 6
records = [struct.unpack('>IIHH', read(symbol('_sim_keys_readlog')+12*i, 12)) for i in range(6)]
assert bytes(r[2] for r in records) == b'aBcc\x08\x0d', records
assert all(r[3] == 0 for r in records), 'UI reads unexpectedly use a gameplay cutoff'
assert value('_sim_keys_waits') > 0, 'native editor never waited for input'
assert value('_sim_keys_live', 2) == value('_sim_keys_pending', 2) == 1
h11 = value('_h11')
# The panel's pending row click can select a different slot after the blocking
# editor returns. Check the changed name itself, not the final selection cursor.
names = []
for slot in range(8):
    name_ptr = int.from_bytes(read(h11+0x4fcc+4*slot, 4), 'big')
    names.append(read(name_ptr, 24).split(b'\0', 1)[0])
assert names.count(b'aBc') == 1, names
edited_slot = names.index(b'aBc')
name = names[edited_slot]
assert value('_sim_options_entries') == value('_sim_options_returns') == 2
assert value('_sim_suspended', 2) == 0 and value('_sim_input_recoveries') == 0
assert all(s['simulation']['input_recoveries'] == 0 for s in samples)
final = samples[-1]['simulation']
resumed = [s for s in samples if s['simulation']['options_returns'] == 2]
assert len(resumed) >= 20, 'insufficient world progression after native UI return'
for before, after in zip(resumed, resumed[1:]):
    assert after['simulation']['consumed']-before['simulation']['consumed'] == 2
print(f'Native save editor retained {name!r} after shift/repeat/backspace/return; '
      f'slot {edited_slot}, {len(resumed)-1} resumed world ticks, balanced options pause, zero recovery')
print('Console records:', records)
