#!/usr/bin/env python3
"""Inspect superseded publications and available beam-position evidence."""
import json,struct,sys,collections
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());t=barto.load(p/'trace.bin');rows=[]
for f in t.fields[117:121]:
 types=collections.Counter();writes=[];planes=[];starts=[]
 for j,off in enumerate(range(0,len(f.dma),f.dma_size)):
  reg=struct.unpack_from('<H',f.dma,off)[0];data=struct.unpack_from('<Q',f.dma,off+2)[0];addr=struct.unpack_from('<I',f.dma,off+12)[0];typ=struct.unpack_from('<h',f.dma,off+29)[0];types[typ]+=1
  if typ==2 and addr in (0xdff080,0xdff082):writes.append(dict(slot=j,line=j//227,hpos=j%227,reg=hex(reg),data=hex(data),address=hex(addr)))
  if typ==6:planes.append(j)
  if typ==3 and addr in (67236,68264):starts.append(dict(slot=j,line=j//227,hpos=j%227,address=addr))
 events=[]
 for order,(pc,c,r) in enumerate(t.instructions(f)):
  if pc in (m['game_base']+0x7140,m['game_base']+0x35332,m['game_base']+0x7500):events.append(dict(order=order,site=hex(pc-m['game_base']),copper=r[8] if pc==m['game_base']+0x35332 else None))
 rows.append(dict(field=f.index,dma_types=dict(types),cpu_copper_writes=writes,copper_starts=starts,bitplane_first_slot=min(planes),bitplane_last_slot=max(planes),events=events))
report=dict(rows=rows,scope='Saved event order and DMA record positions only. Serialized DMA slots use227 positions per line (barto_gdbserver.cpp), not the internal256 stride. CPU writes use generic operation codes and are identified by address. Instruction order alone is not a beam timestamp.')
(p/'publication-dma-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
