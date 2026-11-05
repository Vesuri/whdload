import sys,struct,json,collections
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
p=Path(sys.argv[1]);t=barto.load(p/'trace.bin');rows=[];memory=bytearray(t.chip)
for f in t.fields:
 fetch={};planes={};writes=[]
 for i,o in enumerate(range(0,len(f.dma),f.dma_size)):
  typ=f.dma[o+29];reg=struct.unpack_from('<H',f.dma,o)[0];addr=struct.unpack_from('<I',f.dma,o+12)[0]
  if typ==6 and 0x110<=reg<0x11a:
   fetch[addr]=i;planes.setdefault(reg,addr)
  if typ==5 and reg==0 or typ==2 and reg in (0x1101,0x1102,0x1104):
   size=2 if typ==5 else reg & 15
   value=struct.unpack_from('<I',f.dma,o+2)[0] & ((1<<(size*8))-1)
   if addr+size<=len(memory):
    new=value.to_bytes(size,'big');old=bytes(memory[addr:addr+size]);memory[addr:addr+size]=new
    for step in range(0,size,2):
     writes.append((i,addr+step,'blitter' if typ==5 else 'cpu',old[step:step+2]!=new[step:step+2]))
 overlap=[(i,addr,kind,changed) for i,addr,kind,changed in writes if addr in fetch]
 visible=[(i,addr,kind,changed) for i,addr,kind,changed in overlap if i<fetch[addr]]
 if overlap:rows.append(dict(field=f.index,display_writes=len(overlap),before_fetch=len(visible),changed_before_fetch=sum(c for _,_,_,c in visible),kind=dict(collections.Counter(k for _,_,k,_ in overlap)),rows=sorted(set((addr-min(planes.values()))%8000//40 for _,addr,_,_ in visible)),first=visible[:5]))
result=dict(fields=len(t.fields),fields_with_display_writes=len(rows),display_writes=sum(r['display_writes'] for r in rows),before_fetch=sum(r['before_fetch'] for r in rows),changed_before_fetch=sum(r['changed_before_fetch'] for r in rows),details=rows)
(p/'buffer-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2)[:6500])
