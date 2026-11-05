#!/usr/bin/env python3
"""Check actual CPU/blitter writes against selected four-plane display fetches."""
import collections,json,struct,sys
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
p=Path(sys.argv[1]);display=json.loads((p/'display-check.json').read_text());t=barto.load(p/'trace.bin')
assert display['fields']==len(t.fields)==250
planes={int(c,16):[int(v,16) for v in ps] for c,ps in display['bitplanes_by_copper_list'].items()}
owner={addr:c for c,ps in planes.items() for start in ps for addr in range(start,start+8000,2)}
assert len(owner)==32000
known={addr:struct.unpack_from('>H',t.chip,addr)[0] for addr in owner}
boundaries=barto.capture_part_starts(p,t);counts=collections.Counter();examples={}
def records(f):
 for slot,o in enumerate(range(0,len(f.dma),f.dma_size)):
  reg=struct.unpack_from('<H',f.dma,o)[0];value=struct.unpack_from('<Q',f.dma,o+2)[0];addr=struct.unpack_from('<I',f.dma,o+12)[0];typ,extra=struct.unpack_from('<hH',f.dma,o+29)
  assert struct.unpack_from('<H',f.dma,o+36)[0]==65535,('DMA conflict',f.index,slot)
  yield slot,reg,value,addr,typ,extra
for f in t.fields:
 if f.index in boundaries and f.index:known.clear()
 fetch={addr:(slot,value) for slot,reg,value,addr,typ,extra in records(f) if typ==6}
 assert len(fetch)==16000 and len({owner[a] for a in fetch})==1
 last=max(slot for slot,value in fetch.values())
 for slot,reg,value,addr,typ,extra in records(f):
  if typ==6:
   if addr in known:
    if known[addr]!=value:
     counts['fetch_model_mismatch']+=1;examples.setdefault('fetch_model_mismatch',dict(field=f.index,slot=slot,addr=hex(addr),expected=known[addr],actual=value))
    else:counts['fetch_model_match']+=1
   else:counts['fetch_model_unknown']+=1
   known[addr]=value
   continue
  stores=[];kind=None
  if typ==5:
   counts['blitter_dma_records']+=1
   if reg==0:
    assert extra&15==3
    stores=[(addr,value&65535)];kind='blitter'
  elif typ==2 and reg&0xff00==0x1100:
   kind='cpu';width=reg&15
   if width==4:stores=[(addr,(value>>16)&65535),(addr+2,value&65535)]
   elif width==2:stores=[(addr,value&65535)]
   elif width==1 and addr&~1 in owner:
    word=addr&~1
    if word not in known:
     counts['unknown_byte_store']+=1;continue
    old=known[word];new=(old&0xff00)|(value&255) if addr&1 else (old&255)|((value&255)<<8)
    stores=[(word,new)]
   elif width!=1:raise AssertionError(('unsupported CPU store',hex(reg)))
  for addr,value in stores:
   if addr not in owner:continue
   counts[kind+'_framebuffer_words']+=1
   if addr in fetch and slot<last:
    counts[kind+'_selected_before_display_end']+=1
    old=known.get(addr)
    if old is None:counts['selected_write_unknown']+=1
    elif old!=value:
     counts['selected_changed_before_display_end']+=1
     examples.setdefault('selected_changed_before_display_end',dict(kind=kind,field=f.index,slot=slot,addr=hex(addr),old=old,new=value,fetch=fetch[addr]))
   known[addr]=value
result=dict(fields=250,counts=dict(counts),examples=examples,scope='All recorded CPU byte/word/long stores and cycle-timed blitter word stores in the two complete display bitmaps. Fetch values validate the reconstructed memory model. A changed word in the selected bitmap before its last display fetch rejects safe reuse; capture joins discard unknown history.')
(p/'p3-display-writes.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
assert counts['blitter_dma_records']>0,'Missing actual blitter DMA records'
assert counts['cpu_framebuffer_words']>0
assert counts['fetch_model_match']>3900000
assert counts['fetch_model_mismatch']==counts['selected_changed_before_display_end']==counts['selected_write_unknown']==counts['unknown_byte_store']==0
