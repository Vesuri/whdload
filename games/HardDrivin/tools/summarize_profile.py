#!/usr/bin/env python3
"""Summarize a Hard Drivin SPS 0126 trace; offsets refer to decompressed game code.
This reports buffer swaps as candidate publications until independently validated.
"""
import argparse,bisect,collections,hashlib,json,struct
from pathlib import Path
import barto_mmap as barto

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('trace');p.add_argument('--out',required=True);p.add_argument('--counter',type=Path);a=p.parse_args()
 t=barto.load(a.trace);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 if (out/'metadata.json').exists():
  layout=json.loads((out/'metadata.json').read_text())['layout'];base=layout['code_base'];code=(out/'game-code.bin').read_bytes()[:0x11a4e]
 else:
  # Compatibility with the accepted original A500 captures.
  candidates=[];pat=struct.pack('>I',0x11a4e)
  for index in range(4,len(t.slow)-4,2):
   if t.slow[index:index+4]==pat:
    candidate=struct.unpack_from('>I',t.slow,index-4)[0];offset=candidate-0xc00000
    if 0<=offset<len(t.slow)-0x11a4e and t.slow[offset:offset+2]==b'\x4e\xf9':candidates.append(candidate)
  assert len(set(candidates))==1,candidates
  base=candidates[0];code=t.slow[base-0xc00000:base-0xc00000+0x11a4e]
 starts=[i for i in range(0,len(code)-2,2) if code[i:i+2]==b'\x4e\x55']
 def label(pc):
  if pc is None:return 'STOP/unmapped profiler PC'
  if pc==0x7fffffff:return 'interrupt entry'
  if base<=pc<base+len(code):return f'game:${pc-base:05x}'
  return f'other:${pc:08x}'
 pcs=collections.Counter();hits=collections.Counter();dma=collections.Counter();routine=collections.Counter();fields=[]
 for f in t.fields:
  cycles=records=irq=swaps=0
  for pc,c,r in t.instructions(f):
   pcs[pc]+=c;hits[pc]+=1;cycles+=c;records+=1
   irq+=pc==0x7fffffff;swaps+=pc==base+0xb4
   if pc is not None and base<=pc<base+len(code):
    index=bisect.bisect_right(starts,pc-base)-1
    routine[f'game:${starts[index]:05x}' if index>=0 else label(pc)]+=c
   else:routine[label(pc)]+=c
  for i in range(0,len(f.dma),f.dma_size):dma[int(f.dma[i+29])]+=1
  fields.append(dict(index=f.index,cycles=f.cycles,attributed_cycles=cycles,records=records,irq_entries=irq,candidate_swaps=swaps,shot_sha256=hashlib.sha256(f.shot).hexdigest(),instructions_sha256=hashlib.sha256(t.data[f.insn_off:f.insn_end]).hexdigest(),dma_sha256=hashlib.sha256(f.dma).hexdigest()))
  if f.index in (0,len(t.fields)-1):(out/f"field-{f.index:04}.{'png' if f.shot_kind==1 else 'jpg'}").write_bytes(f.shot)
 # Barto uses CPU-cycle units: 256 on PAL 68000, 128 on 68EC020.
 # Convert through the retained unit; a fixed 7 MHz divisor doubles 020 duration.
 o=8+4*len(t.sections)+16
 for _ in range(3):o+=4+struct.unpack_from('<I',t.data,o)[0]
 baseclock,cycleunit=struct.unpack_from('<II',t.data,o)
 elapsed_cycles=sum(f.cycles for f in t.fields);total=sum(pcs.values());seconds=elapsed_cycles*cycleunit/(baseclock*64)
 assert baseclock==28375160 and cycleunit in (128,256), "unvalidated trace clock"
 assert abs(seconds-len(fields)*142102/7093790)<1e-6, "PAL field duration mismatch"
 validated=False
 if a.counter:
  counter=json.loads(a.counter.read_text());assert counter['per_field']==[f['candidate_swaps'] for f in fields], "trace/counter mismatch"
  validated=True
 result=dict(fields=len(fields),baseclock=baseclock,cycleunit=cycleunit,elapsed_cycles=elapsed_cycles,emulated_seconds=seconds,attributed_cycles=total,cycle_coverage=total/elapsed_cycles,candidate_publications=sum(f['candidate_swaps'] for f in fields),candidate_publications_per_second=sum(f['candidate_swaps'] for f in fields)/seconds,frame_counter_validated=validated,
 hottest_instructions=[dict(location=label(pc),cycles=c,share=c/total,hits=hits[pc]) for pc,c in pcs.most_common(40)],
 routine_self_estimates=[dict(location=k,cycles=c,share=c/total) for k,c in routine.most_common(40)],dma_slots=dict(dma),per_field=fields,
 limitations=['Routine self estimates use nearest preceding LINK A5; validate hot boundaries before optimization.',*([] if validated else ['Candidate swaps need independent read-only breakpoint validation before calling them FPS.'])])
 (out/'metrics.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('per_field','routine_self_estimates','hottest_instructions')},indent=2))
if __name__=='__main__':main()
