"""Optimistic captured-instruction saving before dispatch/mask overhead."""
import sys,json
from pathlib import Path
import numpy as np
import barto_mmap as barto
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());base=m['layout']['code_base'];t=barto.load(p/'trace.bin');eligible=False;removed=interior=total=polys=0
pcs=[0x33b8,0x33ba,0x33bc,0x33c0,0x33c2,0x33c4,0x33c8,0x33ca,0x33cc,0x33e2,0x33e4,0x33e6,0x33ea,0x33ec,0x33ee,0x33f2,0x33f4,0x33f6,0x34b2,0x34b4,0x34b6,0x34ba,0x34bc,0x34be,0x34c2,0x34c4,0x34c6]
for f in t.fields:
 assert (f.insn_end-f.insn_off)%76==0
 a=np.frombuffer(t.data,dtype='<u4',count=(f.insn_end-f.insn_off)//4,offset=f.insn_off).reshape(-1,19);pc=a[:,0].astype(np.int64)-base;total+=int((0xffffffff-a[:,1]).sum());select=(pc==0x337c)|np.isin(pc,pcs)|((pc>=0x3410)&(pc<0x34b0))
 for row in a[select]:
  off=int(row[0])-base;c=0xffffffff-int(row[1])
  if off==0x337c:eligible=all(int(row[i]) in [0,0xffffffff] for i in [5,7,8,9]);polys+=eligible
  elif eligible:
   if 0x3410<=off<0x34b0:interior+=c
   else:removed+=c
r=dict(eligible_polygons=polys,total_cycles=total,eliminable_boundary_cycles=removed,eligible_interior_cycles=interior,optimistic_saved_share_percent=100*(removed+interior*.25)/total,assumptions='Keep native final-plane calculation for outgoing D2/flags; eliminate first three boundary plane load/xor/and instructions, retain equal-cost RMW store; assume 25% saving on all eligible interior word stores; charge ZERO dispatch, mask inversion, alignment or loop overhead. A price estimate, not a measured replacement.')
(p/'solid-rewrite-price.json').write_text(json.dumps(r,indent=2)+'\n');print(p.name,r,flush=True)
