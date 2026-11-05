#!/usr/bin/env python3
"""Calibrated CPU/DMA costs for an instruction trace, excluding partial physics calls."""
import argparse,collections,json,re,struct,sys
from functools import lru_cache
from pathlib import Path
import barto_mmap as barto
from harddrivin_report import Namer,analyse,contexts
from machine_profiles import banks,PROFILES
class Memory:
 def __init__(self,items):self.items=items
 def read(self,a,n):
  for base,b in self.items:
   if base<=a and a+n<=base+len(b):return b[a-base:a-base+n]
 @lru_cache(maxsize=131072)
 def word(self,a):
  b=self.read(a,2);return struct.unpack('>H',b)[0] if b else None
 def long(self,a):
  b=self.read(a,4);return struct.unpack('>I',b)[0] if b else None
 def cstr(self,a):
  b=self.read(a,40);return b.split(b'\0')[0].decode('latin1') if b else ''
def report(out,listing):
 meta=json.loads((out/'metadata.json').read_text());layout=meta['layout'];code=layout['code_base'];t=barto.load(out/'trace.bin')
 text=listing.read_text(encoding='latin1')
 def sym(n):return int(re.search(r'^'+re.escape(n)+r'\s+00:([0-9a-fA-F]+)',text,re.M)[1],16)
 slave=layout['published']-sym('_code_start');blit=slave+sym('_blitwait');blit_end=slave+sym('_dbfwait1')
 items=[(base,(out/('anchor-'+name+'.bin')).read_bytes()) for name,base,size in banks(meta['configuration'])]
 mem=Memory(items);rr=[(code,code+layout['regions'][0]['size'],'game',code),(slave,slave+(out/'slave.slave').stat().st_size,'slave',slave)]
 supported=PROFILES[layout['profile']][-1]=='trace'
 namer=Namer(rr,mem)
 if supported:self_c,incl,calls,edges,pcs,kinds,byctx=analyse(t,mem,namer,t.fields)
 else:self_c,incl,calls,edges,pcs,kinds,byctx=[collections.Counter() for _ in range(7)]
 total=sum(f.cycles for f in t.fields);attributed=sum(kinds.values());dma=collections.Counter();per=[];physics=[];physics_own=[];active=None;own=None;irq=False
 ranges=contexts(t,t.fields) if supported else []
 entry_sp=next((regs[15] for f in t.fields for pc,c,regs in (t.instructions(f) if supported else []) if pc==code+0xcda4),None)
 main=next(((lo,hi) for lo,hi in ranges if entry_sp is not None and lo<=entry_sp<hi),None)
 for f in t.fields:
  swaps=0
  for pc,c,r in (t.instructions(f) if supported else []):
   if pc==0x7fffffff:irq=True
   if pc==code+0x44:irq=True
   in_main=main is not None and main[0]<=r[15]<main[1] and pc!=0x7fffffff
   if pc==code+0xcda4 and in_main:active=0;own=0
   if active is not None and in_main:
    active+=c
    if pc is not None and code+0xcda4<=pc<code+0xcdf8:own+=c
   if pc==code+0xcdb0 and active is not None and in_main:
    physics.append(active);physics_own.append(own);active=None
   if pc is not None and pc!=0x7fffffff and mem.word(pc)==0x4e73:irq=False
   swaps+=pc==code+0xb4
  for value in f.dma[29::f.dma_size]:dma[int(value)]+=1
  per.append(dict(index=f.index,swaps=swaps))
 for i in [0,len(t.fields)//2,len(t.fields)-1]:
  f=t.fields[i];(out/f'field-{i:04}.jpg').write_bytes(f.shot)
 o=8+4*len(t.sections)+16
 for _ in range(3):o+=4+struct.unpack_from('<I',t.data,o)[0]
 clock,unit=struct.unpack_from('<II',t.data,o);seconds=len(t.fields)*142102/7093790
 def cost(lo,hi):return sum(v for pc,v in pcs.items() if pc is not None and lo<=pc<hi)
 def rows(c):return [dict(routine=k,cycles=v,share=v/total,calls=calls[k]) for k,v in c.most_common(40)]
 result=dict(physics_stack_context=main,fields=len(t.fields),seconds=seconds,trace_clock=clock,cycle_unit=unit,elapsed_cycles=total,attributed_cycles=attributed,coverage=attributed/total,swaps=sum(v['swaps'] for v in per),per_field=per,self=rows(self_c),inclusive=rows(incl),dma_slots=dict(dma),dma_share={str(k):v/sum(dma.values()) for k,v in dma.items()},blitter_check_wait_cycles=cost(blit,blit_end),wait_740_cycles=cost(code+0x740,code+0x750),submit_750_own_cycles=cost(code+0x750,code+0x760),physics_completed_calls=len(physics),physics_completed_cycles=sum(physics),physics_cycles_per_completed_call=sum(physics)/len(physics) if physics else None,physics_completed_call_cycles=physics,physics_own_cycles_per_completed_call=sum(physics_own)/len(physics_own) if physics_own else None,limitations=['Self shares use call-target-aware routine boundaries.','Physics counts only complete entry-to-RTS calls, excluding traced interrupt work.','Wait routine costs include checking/branch overhead.'])
 if supported:
  assert .99<=result['coverage']<=1.01,'trace lacks reliable instruction timing'
  assert abs(total*unit/(clock*64)-seconds)<1e-6
 else:
  for key in ['swaps','attributed_cycles','coverage','self','inclusive','blitter_check_wait_cycles','wait_740_cycles','submit_750_own_cycles','physics_completed_calls','physics_completed_cycles','physics_cycles_per_completed_call','physics_completed_call_cycles']:result[key]=None
  result['limitations']=['This CPU backend does not provide validated instruction timing; use independent swap counts. DMA records remain available.']
 result['instruction_timing_supported']=supported
 cfg=(out/'emulator.uae').read_text()
 result['blitter_dma_recording_supported']='blitter_cycle_exact=true' in cfg
 if not result['blitter_dma_recording_supported']:result['limitations'].append('Effective blitter_cycle_exact=false: absent blitter DMA records are unavailable activity, not zero blitter use.')
 (out/'window-metrics.json').write_text(json.dumps(result,indent=2)+'\n');print(out.name,result['swaps'],result['physics_cycles_per_completed_call'],flush=True)
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('listing',type=Path);a=p.parse_args();report(a.out,a.listing)
