#!/usr/bin/env python3
"""Native keyboard route: fresh race, record, Replay Menu / Save Replay.
Run on a freshly booted ordinary runtime; RUNTIME_CAPTURE selects evidence.
No guest writes or fixture calls. The output directory must already exist.
"""
import os,subprocess,sys,json,shutil
from pathlib import Path
resume='--from-main' in sys.argv;cap=Path(os.environ['RUNTIME_CAPTURE']);log=(cap/'route.log').open('a' if resume else 'w')
def run(*args):subprocess.run([sys.executable,*args],check=True,stdout=log,stderr=subprocess.STDOUT)
if not resume:run('tools/runtime_anchor.py',str(cap/'start'))
from runtime_lifecycle_probe import key,fields,snapshot
# Preserve snapshots on disk while keeping terminal output concise.
def snap(n):
 from contextlib import redirect_stdout
 with redirect_stdout(log):return snapshot(n)
def tap(k):key(k,1);fields(10);key(k,0);fields(10)
if not resume:tap(0x45);tap(0x44);fields(80);snap('menu')
key(0x44,1);fields(50);key(0x44,0);fields(300);s=snap('startup');assert s['mode']==1
tap(0x44);fields(100);s=snap('active');assert s['mode']==0 and s['active_rate']==50 and s['consumer']<200
run('tools/runtime_replay_record.py')
tap(0x45);fields(40);s=snap('replay-ready');assert s['mode']==2 and s['recorded_length']==s['imported']==s['consumer']
tap(0x44);fields(30)
for _ in range(4):tap(0x4d)
tap(0x44);fields(40);snap('save-dialog')
for k in [0x4e]*7+[0x41]*7+[0x20,0x04,0x14,0x12,0x21,0x14]:tap(k)
snap('save-name');tap(0x44);fields(100);snap('saved')
f=Path('tmp/run/default/.run/dh1/data/a4test.rpl');assert f.is_file(),'Native save has not produced a host file; inspect write caching'
shutil.copyfile(f,cap/'a4test.rpl');print('Native save complete:',f.stat().st_size,'bytes',flush=True)
