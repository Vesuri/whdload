#!/usr/bin/env python3
"""Validate the current W3 twin boot, with bounded debugger continuation."""
import argparse,json,os,re,signal,struct,sys,threading
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('entry',type=Path);p.add_argument('--step',type=int,default=8);a=p.parse_args()
m=json.loads((a.entry/'entry.json').read_text());listing=(a.entry/'slave.lst').read_text(encoding='latin1')
def label(name):return int(re.search(r'^'+name+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
slave=m['entry']['game_anchor']-label('tape_game_anchor');state=r.read(r.locate());remaining=a.step-state['game_steps'];assert remaining>0
# Check the matched listing before arming the common byte-check failure offset.
cmd='gdb '+''.join(f'break *{slave+at:#x}\n' for at in [label('perf_check_bytes')+0x18,label('sound_queue_fail'),label('sound_div_fail')])+f'break *{state["game_anchor"]:#x}\nignore $bpnum {remaining-1}'
reply=r.command(cmd)
timer=threading.Timer(55,lambda:os.kill(int((r.ROOT/'tmp/run/default/.run/gdb.pid').read_text()),signal.SIGINT));timer.start()
try:reply+=r.command('gdb continue')
finally:timer.cancel()
state=r.read(r.locate());reply+=r.command('gdb info registers pc d0 d1 d2 d4 a0 a1');r.command('gdb delete')
(a.entry/'twin-check.txt').write_text(reply);assert state['game_steps']==a.step, (state,reply)
raw=(r.ROOT/'tmp/build/route-ram.bin').read_bytes();result={'step':a.step,'sha256':m['slave_sha256']}
for marker in [b'RBSLOAD1',b'RBSQUE01',b'RBSDIV01']:
 at=raw.find(marker);assert at>=0
 result[marker.decode()]=dict(address=r.DUMP_BASE+at,values=struct.unpack_from('>3I',raw,at+8))
assert result['RBSQUE01']['values'][1]>0
assert result['RBSDIV01']['values'][1]>result['RBSDIV01']['values'][2]>=65026
(a.entry/'sound-headers.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
