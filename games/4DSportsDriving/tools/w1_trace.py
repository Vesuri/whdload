#!/usr/bin/env python3
"""Measure BLIT handler entries and audit the primitive-drawing subtree."""
import sys,json,collections
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
from profile_report import Memory
p=Path(sys.argv[1]);t=barto.load(p/'trace.bin');meta=json.loads((p/'anchor.json').read_text());g=meta['game_base']
m=Memory(t,(p/'memory.bin').read_bytes(),meta.get('memory_base',0x200000))
e=m.long(4); gfx=m.long(e+0x9c); handler=m.long(e+0xa0)
print('BLIT handler',hex(handler),'gfx',hex(gfx))
level3=m.long(0x6c);irq_vectors={m.long(0x60+4*n) for n in range(1,8)}-{None,0};irq=None;irq_costs=collections.Counter();irq_counts=collections.Counter()
active=False; depthsp=0; counts=collections.Counter(); callees=collections.Counter(); last=None
boundaries=barto.capture_part_starts(p,t)
for f in t.fields:
 if f.index in boundaries:active=False;last=None;irq=None
 for pc,c,r in t.instructions(f):
  if irq and pc in irq_vectors:irq['nested']+=1
  if pc==level3 and irq is None:
   irq={'sp':r[15],'cycles':0,'blit':False,'nested':0}
  if irq:
   irq['cycles']+=c
   if pc==handler:irq['blit']=True
   if pc is not None and m.word(pc)==0x4e73:
    if irq['nested']:
     irq['nested']-=1
     continue
    tag='with_blit' if irq['blit'] else 'without_blit'
    irq_costs[tag]+=irq['cycles'];irq_counts[tag]+=1;irq=None
  if pc==g+0xab82: active=True;depthsp=r[15];counts['drawing_calls']+=1
  if pc==handler+10 and r[0]:counts['nonempty_qblit']+=1
  if pc==handler+0x1a0 and r[0]&0xffff:counts['nonzero_a2']+=1
  if pc==handler:
   counts['blit_entries']+=1
   if active:counts['blit_inside_drawing']+=1
  if active and pc is not None and m.read(pc,2)==b'\x4e\xae' and r[14]==gfx and not r[16]&0x2000:
   counts['graphics_lvo_inside_drawing']+=1
  if last and active:
   lp,lr=last;op=m.read(lp,2)
   if op and int.from_bytes(op,'big')&0xffc0==0x4e80 and lr[15]>=depthsp-4096 and not lr[16]&0x2000:
    if pc is not None and not g<=pc<g+0x3a04c:callees[hex(pc)]+=1
  if pc==g+0xa9e6:active=False
  if pc is not None and pc!=0x7fffffff:last=pc,r
print(json.dumps(dict(counts),indent=2)); print('external call targets inside drawing',callees)

(p/'w1-trace.json').write_text(json.dumps({'counts':dict(counts),'guest_level3_completed':dict(irq_counts),'guest_level3_cycles':dict(irq_costs),'guest_level3_cycles_per_sampled_field':{k:v/len(t.fields) for k,v in irq_costs.items()},'external_calls':dict(callees),'capture_part_starts':sorted(boundaries),'note':'Guest level-3 costs cover outermost captured level-3 vector entry through its RTE, including nested interrupts (also level 3 when the OS lowers IPL). Native interrupt-vector PCs track nesting; the sentinel also covers other exceptions on 68020 and is not used to infer IRQ nesting. Task-switch returns may use a different stack. Partial handlers at capture joins are excluded. Drawing membership is counted only after a captured entry; scopes crossing a capture join are excluded after the join.'},indent=2)+'\n')
