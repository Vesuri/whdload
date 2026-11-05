#!/usr/bin/env python3
"""Matched live body costs, plus observed production hook/dispatch overhead.
Native clones of inline slices have an artificial RTS: subtract its measured
cost when comparing production paths. Whole-function native RTS is retained.
"""
import argparse,json,re,collections
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--group',choices=['geometry','math','bookkeeping'],default='geometry');a=p.parse_args();cap=a.capture
meta=json.loads((cap/'anchor.json').read_text());g=meta['game_base'];slave=(cap/'slave.slave').read_bytes();sl=meta['marker']-slave.index(b'4DTAPE!!')+32
syms={n:int(v,16)+sl for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(cap/'slave.lst').read_text(encoding='latin1'),re.M)}
names={'geometry':['perf_vertices_body','twin_original_vertices','perf_emit_body','twin_original_emit'],
 'math':['perf_backface_body','math_original_backface','perf_parent_body','math_original_parent'],
 'bookkeeping':['perf_clear_body','book_original_clear','perf_epilogue_body','book_original_epilogue']}[a.group]
starts={syms[n]:n for n in names};kinds=['vertices','emit','backface','parent','clear','epilogue']
def kind(name):return next(k for k in kinds if k in name)
selected={kind(n) for n in names}
hooks={g+off:k for k,off in [('vertices',0x1440),('emit',0x1662),('backface',0xaad4),('parent',0xa756),('clear',0xfc6),('epilogue',0x20c8)] if k in selected}
ranges={}
for k,start,end,terminal in [('vertices','perf_vertices','perf_emit','perf_vertices_exit'),('emit','perf_emit','perf_vertices_body','perf_emit_exit'),('epilogue','perf_epilogue','perf_epilogue_body','perf_epilogue_exit')]:
 if k in selected:ranges[k]=(syms[start],syms[end],syms[terminal])
failure_pcs={syms[n] for n in ('twin_failed','math_failed','book_failed') if n in syms}
active=None;last_by_sp={};pending={};pairs=collections.defaultdict(list);routes=collections.defaultdict(list)
trace=barto.load(cap/'trace.bin')
boundaries=barto.capture_part_starts(cap,trace);current_route={};skipped_entries=0
for f in trace.fields:
 if f.index in boundaries:
  active=None;last_by_sp.clear();pending.clear();current_route.clear()
 for pc,c,r in trace.instructions(f):
  assert pc not in failure_pcs, f'VERIFY failure at {pc:#x}'
  if pc in hooks:
   k=hooks[pc];routes[k].append({'cost':c,'complete':k not in ranges});current_route[k]=len(routes[k])-1
  for k,(lo,hi,last) in ranges.items():
   if pc is not None and lo<=pc<hi and k in current_route:
    routes[k][-1]['cost']+=c
    if pc==last:routes[k][-1]['complete']=True
  if active and pc==active['ret'] and r[15]==active['sp']+4:
   name=active['name'];k=kind(name)
   if name.startswith('perf_'):pending[k]=(active['cost'],current_route.get(k,-1))
   elif k in pending:
    new,route=pending.pop(k)
    pairs[k].append({'new':new,'old':active['cost'],'old_tail':active['last_cost'] if k in ('vertices','emit','clear','epilogue') else 0,'route':route})
   active=None
  # The native clear loop branches back to its first instruction; that is
  # another iteration, not another call.
  if pc in starts and not (active and active['name']==starts[pc] and active['sp']==r[15]):
   assert active is None
   last=last_by_sp.get(r[15]+4)
   off=last-sl+32 if last is not None else -1
   op=int.from_bytes(slave[off:off+2],'big') if 0<=off<len(slave)-1 else 0
   if op&0xff00==0x6100:
    active={'name':starts[pc],'sp':r[15],'ret':last+(4 if op&255==0 else 2),'cost':0,'last_cost':0}
   else:
    # A capture can start after the caller or inside the native clear loop.
    skipped_entries+=1
  # UAE materializes SR lazily: its task stack is the reliable context signal.
  if active and active['sp']-4096<=r[15]<=active['sp']:
   active['cost']+=c;active['last_cost']=c
  if pc is not None and pc!=0x7fffffff:last_by_sp[r[15]]=pc
print(f'Excluded partial calls at capture starts {sorted(boundaries)}; {skipped_entries} entry records lacked a captured caller')
out={}
for k,pp in pairs.items():
 new=sum(p['new'] for p in pp);old=sum(p['old'] for p in pp)
 result={'matched_calls':len(pp),'original_cycles_per_call':old/len(pp),'replacement_cycles_per_call':new/len(pp),'change_percent':100*(new/old-1)}
 complete=[p for p in pp if p['route']>=0 and routes[k][p['route']]['complete']]
 if complete:
  native=sum(p['old']-p['old_tail'] for p in complete);replacement=sum(p['new']+routes[k][p['route']]['cost'] for p in complete)
  result['production_path']={'matched_calls':len(complete),'original_cycles_per_call':native/len(complete),'replacement_cycles_per_call':replacement/len(complete),'change_percent':100*(replacement/native-1),'hook_cycles_per_call':sum(routes[k][p['route']]['cost'] for p in complete)/len(complete)}
 out[k]=result
assert out,'No complete twin pairs'
(cap/'loop-cost.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
