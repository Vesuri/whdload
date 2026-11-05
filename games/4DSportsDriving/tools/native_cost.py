#!/usr/bin/env python3
"""Completed main-task routine costs and remaining object-geometry self time.
This is a workload description, not an FPS or cross-boot speedup measurement.
"""
import argparse,json,re,collections
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from profile_report import Memory
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();cap=a.capture
meta=json.loads((cap/'anchor.json').read_text());g=meta['game_base'];slave=(cap/'slave.slave').read_bytes();sl=meta['marker']-slave.index(b'4DTAPE!!')+32
syms={n:int(v,16)+sl for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
t=barto.load(cap/'trace.bin');mem=Memory(t,(cap/'memory.bin').read_bytes(),meta.get('memory_base',0x200000))
starts={g+0xf00:'object_geometry',g+0xaad4:'backface',g+0xa756:'parent_rotation'}
active={};done=collections.defaultdict(list);costs=collections.Counter();frame=None;frames=[]
boundaries=barto.capture_part_starts(cap,t)
for field in t.fields:
 if field.index in boundaries:active.clear();frame=None
 for pc,c,r in t.instructions(field):
  sp=r[15];costs['total']+=c
  if pc is None or pc==0x7fffffff:continue
  off=pc-g
  if 0xf00<=off<0x21e4 or syms['perf_vertices']<=pc<syms['perf_math_init'] or syms.get('perf_clear_body',0)<=pc<syms.get('bookkeeping_code_end',0):costs['object_self']+=c
  if 0x13b2<=off<0x1440:costs['setup']+=c
  if 0x2062<=off<0x21e4:costs['epilogue']+=c
  if 0xfc6<=off<0xfcc:costs['byte_clear']+=c
  if pc==g+0x7500:
   if frame:frames.append(frame['cycles'])
   frame={'sp':sp,'cycles':0}
  if frame and frame['sp']-0x4000<=sp<=frame['sp']:frame['cycles']+=c
  if pc in starts:
   name=starts[pc];assert name not in active
   active[name]={'sp':sp,'cycles':0}
  for name,state in list(active.items()):
   if state['sp']-0x4000<=sp<=state['sp']:state['cycles']+=c
   if sp==state['sp'] and mem.word(pc)==0x4e75:
    done[name].append(state['cycles']);del active[name]
result={'fields':len(t.fields),'costs':dict(costs),'percent_of_total':{n:100*c/costs['total'] for n,c in costs.items()},
 'completed_calls':{n:{'count':len(cc),'cycles_per_call':sum(cc)/len(cc),'min':min(cc),'max':max(cc)} for n,cc in done.items()},
 'completed_render_intervals':{'count':len(frames),'main_cycles_per_interval':sum(frames)/len(frames) if frames else None},
 'note':'Boundary-partial calls and intervals excluded, including capture joins. Different boot workloads are not a measured speedup; display validation is a separate display_check.py result.'}
(cap/'native-cost.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
