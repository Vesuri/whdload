#!/usr/bin/env python3
"""Phase-5 native keys and read-only state, with a separate evidence log."""
import json,sys,re
from pathlib import Path
from harness import ROOT,server,command,dump,live_regions
from timing_map import decode
out=ROOT/'tmp/phase5'/sys.argv[1];out.mkdir(exist_ok=True)
def cmd(s):
 r=command(s)
 with (out/'actions.jsonl').open('a') as f:f.write(json.dumps(dict(command=s,reply=r))+'\n')
 return r
for arg in sys.argv[2:]:
 op,val=arg.split(':',1)
 if op=='fields':cmd('monitor fields '+val)
 elif op in ('down','up'):cmd('monitor key '+val+' '+('1' if op=='down' else '0'))
 elif op=='tap':
  cmd('monitor key '+val+' 1');cmd('monitor fields 10');cmd('monitor key '+val+' 0');cmd('monitor fields 20')
 elif op=='shot':server.request('shot '+str(out/(val+'.png')))
 elif op=='state':
  base,rr=live_regions(out/val);s=decode(dump(out/val/'data.bin',rr['td-data'],rr['td-data']+0x32a4).read_bytes());(out/val/'state.json').write_text(json.dumps(s,indent=2)+'\n');print(s)
 elif op=='gdb':print(cmd(val))
 else:raise ValueError(op)
