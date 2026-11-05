#!/usr/bin/env python3
"""Save the active later-checkpoint recording using native menu controls."""
import os,json,shutil
from pathlib import Path
from runtime_lifecycle_probe import key,fields,snapshot,cap
log=(cap/'save-route.log').open('w')
def snap(n):
 from contextlib import redirect_stdout
 with redirect_stdout(log):return snapshot(n)
def tap(k):key(k,1);fields(10);key(k,0);fields(10)
tap(0x45);fields(40);s=snap('replay-ready');assert s['mode']==2 and s['recorded_length']==s['imported']==s['consumer']
tap(0x44);fields(30)
for _ in range(4):tap(0x4d)
tap(0x44);fields(40);snap('save-dialog')
for k in [0x4e]*7+[0x41]*7+[0x20,0x04,0x14,0x12,0x21,0x14]:tap(k)
snap('save-name');tap(0x44);fields(100);snap('saved')
f=Path('tmp/run/default/.run/dh1/data/a4test.rpl');assert f.is_file(),'Native save has not produced a host file; inspect write caching'
shutil.copyfile(f,cap/'a4test.rpl');print('Native save complete:',f.stat().st_size,'bytes',flush=True)
