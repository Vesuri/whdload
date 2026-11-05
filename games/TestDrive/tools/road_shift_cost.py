#!/usr/bin/env python3
"""Count renderer self cycles plus sim_ratio calls made by the new lane seed."""
import json,re,sys
from pathlib import Path
from subunit_cost import measure
from amigaxdev import barto
p=Path(sys.argv[1]);result=measure(p,100)
m=json.loads((p/'capture.json').read_text());b=(p/'code.bin').read_bytes();syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
off=m['regions']['td']+0x6390-m['base'];base=int.from_bytes(b[off+2:off+6],'big')-syms['overlay_unload_end'];lo=base+syms['render_overlay_loaded'];hi=base+syms['render_subunit_end'];prev=None;active=False;extra=0
trace=barto.load(p/'trace.bin')
for field in trace.fields:
 for pc,cycles,regs in trace.instructions(field):
  if pc==base+syms['sim_ratio'] and prev is not None and lo<=prev<hi:active=True
  if pc is not None and lo<=pc<hi:active=False
  if active:extra+=cycles
  if pc is not None:prev=pc
result['shared_helper_cycles']=extra;result['percent_including_helper']=100*(result['self_cycles']+extra)/result['total_cycles'];result['limit']=3
assert result['percent_including_helper']<3,result
print(json.dumps(result,indent=2))
