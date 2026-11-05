"""Observe Paula fetches following known DMA restarts; report, do not assume causes."""
import sys,json,struct
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
p=Path(sys.argv[1]);manifest=json.loads((p/'audio-capture.json').read_text());regs={};enabled=[None]*4;pending={};starts=[];timeline=0;fields=0
for part in manifest['parts']:
 # Profiler boundaries may omit an interval; never infer state across them.
 for rec in pending.values():rec['capture_boundary']=True
 regs={};enabled=[None]*4;pending={}
 t=barto.load(p/part['file']);assert len(t.fields)==part['fields']
 for f in t.fields:
  fields+=1
  for i,o in enumerate(range(0,len(f.dma),f.dma_size)):
   typ=f.dma[o+29];r=struct.unpack_from('<H',f.dma,o)[0];v=struct.unpack_from('<I',f.dma,o+2)[0]&65535;adr=struct.unpack_from('<I',f.dma,o+12)[0];now=timeline+i
   if typ==2 and r==0x1102:
    r=adr-0xdff000
    if 160<=r<224:regs[r]=v
    if r==150:
     for c in range(4):
      if not v&(1<<c):continue
      new=bool(v&32768)
      if new and enabled[c] is False and all(c*16+r in regs for r in (160,162,164,166,168)):
       b=c*16;rec=dict(channel=c,cycle=now,pointer=((regs[160+b]<<16)|regs[162+b])&0x1ffffe,length=regs[164+b],period=regs[166+b],volume=regs[168+b]);starts.append(rec);pending[c]=rec
      if not new and c in pending:pending.pop(c)['disabled_before_fetch']=True
      enabled[c]=new
   elif typ==4 and r in (170,186,202,218):
    c=(r-170)//16
    if c in pending:
     rec=pending[c];fetches=rec.setdefault('fetches',[]);fetches.append(dict(address=adr,latency_cycles=now-rec['cycle']))
     if len(fetches)==3:
      pending.pop(c);rec.update(first_fetch=fetches[0]['address'],pointer_match=fetches[1]['address']==rec['pointer'],next_word_match=fetches[2]['address']==rec['pointer']+2)
  timeline+=len(f.dma)//f.dma_size
 del t
for rec in pending.values():rec['capture_boundary']=True
summary=dict(fields=fields,known_restarts=len(starts),first_fetches=sum('first_fetch' in r for r in starts),mismatches=[r for r in starts if r.get('pointer_match') is False],no_fetch=[r for r in starts if 'first_fetch' not in r and not r.get('capture_boundary')],boundary_pending=sum(r.get('capture_boundary',False) for r in starts),scope='First fetch is the documented Agnus pipeline discard; check second against AUDxLC and third against LC+2. Not audible acceptance')
(p/'audio-restarts.json').write_text(json.dumps(dict(summary=summary,starts=starts),indent=2)+'\n');print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in summary.items()},indent=2))
