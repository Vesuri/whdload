#!/usr/bin/env python3
"""Audit actual recorded blitter writes against selected bitplane fetches."""
import argparse,json,struct,collections
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--display-maps',action='store_true',help='Use strict display-check four-plane mapping for an uninstrumented build');a=p.parse_args();cap=a.capture
if a.display_maps:
 display=json.loads((cap/'display-check.json').read_text());assert display['fields']==250
 maps={int(c,16):[int(v,16) for v in planes] for c,planes in display['bitplanes_by_copper_list'].items()}
else:
 beam=json.loads((cap/'render-beam-check.json').read_text());maps={int(c):v['planes'] for c,v in beam['bitmap_maps'].items()}
assert len(maps)==2 and all(len(v)==4 for v in maps.values())
t=barto.load(cap/'trace.bin');assert len(t.fields)==250
sets={c:{addr for start in planes for addr in range(start,start+8000,2)} for c,planes in maps.items()};alladdr=set.union(*sets.values());owner={x:c for c,ss in sets.items() for x in ss}
assert all(len(v)==16000 for v in sets.values()) and not set.intersection(*sets.values())
known={addr:struct.unpack_from('>H',t.chip,addr)[0] for addr in alladdr};boundaries=barto.capture_part_starts(cap,t)
counts=collections.Counter();examples={};rows=[]
def records(f):
 for j,o in enumerate(range(0,len(f.dma),f.dma_size)):
  reg=struct.unpack_from('<H',f.dma,o)[0];data=struct.unpack_from('<Q',f.dma,o+2)[0];addr=struct.unpack_from('<I',f.dma,o+12)[0];typ,extra=struct.unpack_from('<hH',f.dma,o+29)
  yield j,reg,data,addr,typ,extra
for f in t.fields:
 conflicts=sum(struct.unpack_from('<H',f.dma,o+36)[0]!=65535 for o in range(0,len(f.dma),f.dma_size))
 assert conflicts==0,(f.index,'DMA conflicts require explicit reconstruction',conflicts)
 if f.index in boundaries and f.index:known.clear()
 fetch={addr:(j,value) for j,reg,value,addr,typ,extra in records(f) if typ==6}
 assert len(fetch)==16000
 selected={owner[addr] for addr in fetch};assert len(selected)==1;selected=selected.pop();last=max(j for j,v in fetch.values());local=collections.Counter()
 comparable=all(addr in known for addr in fetch)
 difference=sum(known[addr]!=value for addr,(j,value) in fetch.items()) if comparable else None
 start_difference=difference;minimum_difference=difference
 def update_difference(addr,value):
  global difference,minimum_difference
  if comparable and addr in fetch:
   shown=fetch[addr][1]
   difference+=int(value!=shown)-int(known[addr]!=shown)
   minimum_difference=min(minimum_difference,difference)
 for slot,reg,value,addr,typ,extra in records(f):
  if typ==5:counts['blitter_dma_records']+=1
  if typ==6:
   if addr in known:
    key='fetch_model_match' if known[addr]==value else 'fetch_model_mismatch';counts[key]+=1
    if key.endswith('mismatch'):examples.setdefault(key,dict(field=f.index,slot=slot,address=addr,expected=known[addr],observed=value))
   else:counts['fetch_model_unknown']+=1
   # Measured fetch is an authoritative baseline for subsequent comparisons.
   known[addr]=value
  if typ==5 and reg==0:
   assert extra&15==3,(typ,reg,extra)
   counts['blitter_writes']+=1
   if addr not in alladdr:continue
   counts['framebuffer_blitter_writes']+=1
   old=known.get(addr);changed=old is not None and old!=value
   if addr in fetch:
    fslot,fvalue=fetch[addr];category='before_word_fetch' if slot<fslot else 'after_word_fetch';local[category]+=1
    if changed:local[category+'_changed']+=1
    if slot<last:
     local['selected_buffer_writes_before_display_end']+=1
     if changed:
      local['selected_buffer_changed_before_display_end']+=1
      examples.setdefault(category+'_changed',dict(field=f.index,slot=slot,line=slot//227,hpos=slot%227,address=addr,old=old,new=value,fetch_slot=fslot,fetch_value=fvalue))
   update_difference(addr,value)
   known[addr]=value
  # Preserve any explicitly recorded CPU word/long stores to the same memory.
  if typ==2 and reg&0xff00==0x1100 and addr in alladdr:
   width=reg&15
   if width==2:
    update_difference(addr,value&65535);known[addr]=value&65535
   elif width==4:
    update_difference(addr,(value>>16)&65535);known[addr]=(value>>16)&65535
    if addr+2 in alladdr:
     update_difference(addr+2,value&65535);known[addr+2]=value&65535
   else:
    comparable=False;known.pop(addr&~1,None)
   counts['framebuffer_cpu_stores']+=1
 if comparable:
  assert difference==sum(known[addr]!=value for addr,(j,value) in fetch.items())
  counts['whole_field_buffer_comparisons']+=1
  if minimum_difference>0:counts['fields_never_matching_single_buffer_state']+=1
 counts.update(local);rows.append(dict(field=f.index,selected_copper=selected,counts=dict(local),whole_field_comparable=comparable,start_difference=start_difference,end_difference=difference,minimum_difference=minimum_difference))
assert counts['blitter_dma_records']>0,'No actual blitter DMA records; configured preference was insufficient'
assert counts['fetch_model_mismatch']==0,'Cannot certify buffer-state comparison with missing writes'
result=dict(dma_conflicts=0,fields=250,counts=dict(counts),examples=examples,rows=rows,scope='Actual blitter writes and display fetches in the separately configured cycle-timed-blitter emulator. Model compares recorded writes with fetches, rebaselines from each fetch and discards history at capture joins. Changed writes before/after word fetch establish reuse timing, not on their own a complete-frame tearing verdict or hardware CPU performance claim. A positive minimum_difference with complete initial contents means the displayed 16000 words never equal any instantaneous buffer state during that field, considering every recorded write; zero fetch-model mismatches are required. Capture-join incomplete states excluded.')
(cap/'render-blitter-overlap.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
