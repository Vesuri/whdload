#!/usr/bin/env python3
"""Read-only TFX presentation/vblank observer and independent full-trace capture."""
import argparse,json,os,re,struct,shutil
from pathlib import Path
from replay_flight import ROOT,run,sha
from amigaxdev import barto
MARKERS={'swap':0x19fc,'publish':0x4c474,'vblank':0x4d2de}
CLOCK=0x4d884

def capture(mode):
 def observe(cmd,dump,bases,hs,out):
  base=bases[0]
  def clock():return struct.unpack('>I',dump('clock.bin',base+CLOCK,4))[0]
  initial=clock()
  for i,(a,h) in enumerate(zip(bases,hs)):dump(f'entry-hunk{i}.bin',a,h['size'])
  # Assert exact unmodified publisher / clock increment opcodes and destinations.
  assert dump('publish-op.bin',base+MARKERS['publish'],6)==bytes.fromhex('23c800dff080')
  assert dump('vblank-op.bin',base+MARKERS['vblank'],6)==bytes.fromhex('52b9')+struct.pack('>I',base+CLOCK)
  cmd('delete breakpoints')
  result={'mode':mode,'base':base,'initial_clock':initial,'markers':MARKERS,'events':[]}
  if mode=='trace':
   path=out/'full.trace';cmd(f'monitor profile 20 "" "{path}"')
   final=clock();t=barto.load(path);events=[];records=0;vblanks=0
   for f in t.fields:
    for pc,cost,r in t.instructions(f):
     records+=1
     if pc-base not in MARKERS.values():continue
     kind=next(k for k,v in MARKERS.items() if v==pc-base)
     if kind=='vblank':vblanks+=1
     events.append({'kind':kind,'relative_clock':vblanks,'field':f.index,'copper':r[8] if kind=='publish' else None})
   assert records>10000 and vblanks>=18,(records,vblanks)
   # Snapshot at final vsync: no game instruction executes between profiler stop
   # and debugger stop. Reconstruct absolute game clock backwards from that value.
   for event in events:event['clock']=final-vblanks+event.pop('relative_clock')
   result.update(final_clock=final,instruction_records=records,trace_vblanks=vblanks,fields=len(t.fields),trace_sha256=sha(path),events=events)
   (out/('last.png' if t.fields[-1].shot_kind else 'last.jpg')).write_bytes(t.fields[-1].shot)
  else:
   ticks=0
   for kind,off in MARKERS.items():cmd(f'break *{base+off:#x}')
   while True:
    reply=cmd('continue');match=re.search(r'Breakpoint \d+, (0x[0-9a-f]+)',reply);assert match,reply[-500:]
    cmd('maintenance flush register-cache')
    pc=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $pc'))[1],16)
    assert pc==int(match[1],16)
    kind=next(k for k,v in MARKERS.items() if base+v==pc)
    raw_clock=clock()
    ticks+=kind=='vblank'
    now=initial+ticks # count executed vblank markers; raw RAM can lag copyback cache
    copper=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $a0'))[1],16) if kind=='publish' else None
    result['events'].append({'kind':kind,'clock':now,'raw_clock':raw_clock,'copper':copper})
    if now>=initial+22:break
  for i,(a,h) in enumerate(zip(bases,hs)):dump(f'exit-hunk{i}.bin',a,h['size'])
  (out/'counts.json').write_text(json.dumps(result,indent=2))
  print(mode,'events',len(result['events']),'clock',initial,flush=True)
 return observe

def main():
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['observe','trace'],required=True);p.add_argument('--output',required=True);p.add_argument('--seed',required=True);a=p.parse_args()
 os.chdir(ROOT);out=Path(a.output).resolve();seed=Path(a.seed).resolve()
 run('040',out,seed,capture(a.mode))
 shutil.copy(__file__,out/'count_frames.py')
if __name__=='__main__':main()
