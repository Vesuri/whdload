#!/usr/bin/env python3
"""Check complete copies for any foreign instruction, independently of VBR."""
import json,os,re,sys
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from gpc_report import regions
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());h=m['code_base'];t=barto.load(p/'trace.bin')
os.environ['SLAVE']=str(p/'slave.slave');ram=(p/'before.bin').read_bytes()
sb=next(lo for lo,hi,n,o in regions(ram,m['base']) if n=='slave')
listing=(p/'slave.slave.lst').read_text(encoding='latin1')
def symbol(n):return sb+int(re.search(r'^'+n+r'\s+00:([0-9A-F]+)$',listing,re.M)[1],16)
enter,leave=symbol('sim_latch_enter'),symbol('sim_latch_leave')
tail=ram[leave-m['base']:leave-m['base']+40].find(bytes.fromhex('4cdf7fff4e75'))
assert tail>=0
leave_rts=leave+tail+4
active=None;whole=None;copies=[];latches=[]
for f in t.fields:
 for pc,c,r in t.instructions(f):
  if pc==enter:
   assert whole is None
   whole={'field':f.index,'cycles':0}
  if whole is not None:
   whole['cycles']+=c
   if pc==leave_rts:latches.append(whole);whole=None
  if pc==h+0xa6f2:
   assert active is None
   active={'field':f.index,'cycles':0,'foreign_instructions':0,'first_foreign_pc':None}
  if active is not None:
   active['cycles']+=c
   if not h+0xa6f2<=pc<=h+0xa776:
    active['foreign_instructions']+=1
    if active['first_foreign_pc'] is None:active['first_foreign_pc']=pc
   if pc==h+0xa776:copies.append(active);active=None
assert copies and latches
assert all(x['foreign_instructions']==0 for x in copies),[x for x in copies if x['foreign_instructions']]
result={'complete_copies':len(copies),'foreign_instructions_during_copy':0,'max_copy_cycles':max(x['cycles'] for x in copies),'complete_latches':len(latches),'max_inclusive_latch_cycles':max(x['cycles'] for x in latches),'scope':'Only complete copies/latches; whole-latch cost includes any IRQ after Enable. Copy check rejects every foreign PC, including IRQs regardless of vector base.','copies':copies,'latches':latches}
(p/'latch-audit.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ['copies','latches']})
