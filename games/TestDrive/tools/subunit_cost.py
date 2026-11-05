#!/usr/bin/env python3
"""Conservative A500 self-cycle budget for the complete TD sub-unit patch."""
import argparse,json,re
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from audit_simulation import ranges

def measure(p,limit=3):
 meta=json.loads((p/'capture.json').read_text());assert json.loads((p/'machine.json').read_text())['cpu']=='68000'
 syms={n:int(a,16) for n,a in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
 mem=(p/'code.bin').read_bytes();off=meta['regions']['td']+0x6390-meta['base'];slave=int.from_bytes(mem[off+2:off+6],'big')-syms['overlay_unload_end']
 lo=slave+syms['render_overlay_loaded'];hi=slave+syms['render_subunit_end']
 hooks=set()
 for r in ranges():
  if r['hunk']=='h4' and r['label'].startswith('render_'):hooks.update(range(meta['regions']['h4']+r['offset'],meta['regions']['h4']+r['offset']+r['size'],2))
 trace=barto.load(p/'trace.bin');total=cost=calls=0
 for field in trace.fields:
  for pc,cycles,regs in trace.instructions(field):
   total+=cycles
   if pc==slave+syms['render_lateral_main']:calls+=1
   if pc is not None and (lo<=pc<hi or pc in hooks):cost+=cycles
 assert abs(total-len(trace.fields)*142102)<=142102,'invalid PAL trace cycle total'
 result=dict(fields=len(trace.fields),main_calls=calls,self_cycles=cost,total_cycles=total,percent=100*cost/total,limit=limit)
 assert calls and result['percent']<=limit,result
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--limit',type=float,default=3);a=p.parse_args();print(json.dumps(measure(a.capture,a.limit),indent=2))
