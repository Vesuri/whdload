#!/usr/bin/env python3
"""Compare recorded CPU writes against display fetches, preserving uncertainty."""
import json,struct,sys,collections
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=Path(sys.argv[1]);t=barto.load(p/'trace.bin');f=t.fields[118]
def records(f):
 for j,o in enumerate(range(0,len(f.dma),f.dma_size)):
  yield j,struct.unpack_from('<H',f.dma,o)[0],struct.unpack_from('<Q',f.dma,o+2)[0],struct.unpack_from('<I',f.dma,o+12)[0],struct.unpack_from('<h',f.dma,o+29)[0]
fetches={}
for j,reg,data,addr,typ in records(f):
 if typ==6:fetches.setdefault(addr,[]).append((j,data))
counts=collections.Counter();examples={};widths=collections.Counter()
for j,reg,data,addr,typ in records(f):
 if typ!=2 or (reg&0xff00)!=0x1100:continue
 widths[reg&15]+=1
 if addr not in fetches:continue
 assert reg&15==2,'Need explicit non-word bus write support'
 fs=fetches[addr];assert len(fs)==1,'Repeated fetch needs distinct handling'
 slot,value=fs[0];category=('before' if j<slot else 'after')+('_same' if data==value else '_different')
 counts[category]+=1
 examples.setdefault(category,dict(write_slot=j,write_line=j//227,fetch_slot=slot,fetch_line=slot//227,address=hex(addr),write_value=hex(data),fetched_value=hex(value)))
report=dict(field=118,displayed_words=len(fetches),cpu_write_widths=dict(widths),counts=dict(counts),examples=examples,scope='Actual word writes to addresses fetched by the displayed bitplanes in the same field. After/different proves a displayed old word was subsequently replaced. Before/same alone does not prove it changed from the initial frame; initial-content reconstruction is needed to establish mixed-frame output. No tearing or safety verdict yet.')
(p/'display-buffer-write-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
