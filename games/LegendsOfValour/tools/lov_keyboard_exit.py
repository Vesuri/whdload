#!/usr/bin/env python3
"""Observe real game-loop exit: cancel read, remove collector, close native console."""
import argparse
import os
import re
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('capture', type=Path)
p.add_argument('--base', type=lambda x: int(x,0), default=0xc00000)
a = p.parse_args()
root = a.capture
listing = (root/'slave.lst').read_text(errors='replace')
slave = int(re.search(r'^slave (0x[0-9a-f]+)', (root/'anchor.txt').read_text(), re.M)[1],16)
size = (root/'code.bin').stat().st_size

def symbol(name):
    return slave+int(re.search(r'^'+name+r'\s+00:([0-9A-F]{8})\s*$', listing,re.M)[1],16)

def lov(*args):
    return subprocess.check_output(['python3','tools/lov.py',*args],text=True)

def until(address, label):
    text = lov('until',hex(address),hex(symbol('_c2p_abort')))
    (root/(label+'-stop.txt')).write_text(text)
    match = re.search(r'^Breakpoint \d+, (0x[0-9a-f]+)',text,re.M)
    assert match and int(match[1],16)==address, text

def dump(address, size, label):
    path = Path(f'/tmp/lov-key-exit-{os.getpid()}.bin')
    try:
        lov('gdb',f'dump binary memory {path} {address:#x} {address+size:#x}')
        data = path.read_bytes()
        (root/(label+'.bin')).write_bytes(data)
        assert len(data)==size
        return data
    finally:
        path.unlink(missing_ok=True)

until(symbol('_sim_keys_stopped'),'collector-stopped')
mem = dump(a.base,size,'collector-stopped')
def value(name,size=4):
    at=symbol(name)-a.base
    return int.from_bytes(mem[at:at+size],'big')
assert value('_sim_keys_task')==value('_sim_keys_live',2)==value('_sim_keys_pending',2)==0
assert value('_sim_keys_error',2)==0 and value('_sim_keys_stopping',2)==1
assert value('_sim_keys_reads')==4
assert value('_timing_keys_sent')==7 and value('_timing_keys_done',2)==1
port = value('_sim_keys_port')
owner = int.from_bytes(dump(port+16,4,'restored-port-owner'),'big')
assert owner==value('_sim_keys_owner')!=0
hunks=symbol('_hunks')-a.base
h1=int.from_bytes(mem[hunks+4:hunks+8],'big')
until(h1+0x2740,'native-console-closed')
dump(a.base,size,'native-console-closed')
print('Pending console read cancelled; collector removed/freed; original port owner restored; native close returned')
