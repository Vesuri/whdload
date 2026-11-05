#!/usr/bin/env python3
"""Measure completed nonblocking main-loop work against its field budget.
Includes interruptions/preemption from post-wait h4:$198 through next h4:$16A;
excludes only the explicit frame wait. Never bridge a partial trace boundary.
"""
import argparse,json,statistics
from pathlib import Path
import _amigaxdev
from amigaxdev import barto

def measure(t,h4,frame,period):
 start=None;rows=[];base=0;starts=[];largest=0
 for f in t.fields:
  within=0
  for pc,c,r in t.instructions(f):
   tick=base+within
   if pc==h4+0x198 and r[13]==frame:
    assert start is None,'new iteration before previous work reached wait'
    start=tick;starts.append(tick)
   if pc==h4+0x16a and r[13]==frame and start is not None:
    rows.append(tick-start);start=None
   within+=c;largest=max(largest,c)
  # A record crossing a field boundary is charged wholly to one field.
  # Sum records continuously, avoiding an artificial gap/overlap at the edge.
  base+=within
 assert abs(base-sum(f.cycles for f in t.fields))<=largest+256,'trace cycle accounting mismatch'
 assert len(rows)>=8,'not enough complete main-loop iterations'
 field_cycles=statistics.mean(f.cycles for f in t.fields)
 assert all(0<x<period*field_cycles for x in rows),'measured simulation work exceeds selected period'
 return dict(status='PASS',complete_iterations=len(rows),period=period,field_cycles=field_cycles,
             work_cycles=rows,max_work_fields=max(rows)/field_cycles,
             max_period_percent=100*max(rows)/(field_cycles*period),
             mean_period_percent=100*statistics.mean(rows)/(field_cycles*period),
             scope='Observed nonblocking work including interrupt/preemption time, not a universal worst-case bound; deadline spacing is checked separately')
def check(p):
 m=json.loads((p/'capture.json').read_text());raw=(p/'trace-start/code.bin').read_bytes()
 off=m['frame']-16-m['base'];period=int.from_bytes(raw[off:off+4],'big');assert period in (2,5)
 return measure(barto.load(str(p/'trace.bin')),m['regions']['h4'],m['frame'],period)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('captures',nargs='+',type=Path);a=p.parse_args()
 print(json.dumps({str(x):check(x) for x in a.captures},indent=2))
