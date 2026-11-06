#!/usr/bin/env python3
"""Palette observations, not a proof that an intermittent glitch is absent."""
import json,sys,struct,hashlib,collections
from pathlib import Path
from replay_flight import barto

def report(root):
 base=json.loads((root/'segments.json').read_text())[0]
 machine=json.loads((root/'launch.json').read_text())['machine']
 offsets={'SetPal':0x4a874,'DiffSetPal':0x4a8f6,'BlankPalette':0x4ab04,'WhitePalette':0x4ab56} if machine=='020' else {'SetPal':0x4c32c,'DiffSetPal':0x4c3ae,'BlankPalette':0x4c5bc,'WhitePalette':0x4c60e}
 rows=[]
 for p in sorted(root.glob('*.trace')):
  t=barto.load(p);f=t.fields[-1];raw=f.aga_colors
  assert len(raw)==1024
  rgb=b''.join(raw[i+1:i+4] for i in range(0,1024,4))
  calls=collections.Counter();instructions=0;unresolved=0
  for pc,cost,regs in t.instructions(f):
   if pc is None or pc==0x7fffffff:
    unresolved+=1;continue
   instructions+=1
   for name,off in offsets.items():
    if pc==base+off:calls[name]+=1
  pal=root/(p.stem+'-palette.bin');mismatch=None
  # Initial 020 survey used the wrong hunk, so those dumps are invalid.
  if pal.exists() and (root/'palette-pointer.bin').exists():
   d=pal.read_bytes();assert len(d)==768
   mismatch=[i for i in range(256) if d[i*3:i*3+3]!=rgb[i*3:i*3+3]]
  elif pal.exists() and machine=='040':
   d=pal.read_bytes();assert len(d)==768
   mismatch=[i for i in range(256) if d[i*3:i*3+3]!=rgb[i*3:i*3+3]]
  rows.append(dict(frame=p.stem,trace_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),instructions=instructions,unresolved_trace_records=unresolved,palette_calls=dict(calls),hardware_rgb_sha256=hashlib.sha256(rgb).hexdigest(),saturated_yellow=[i for i in range(256) if rgb[i*3]>200 and rgb[i*3+1]>200 and rgb[i*3+2]<60],software_palette_mismatches=mismatch))
 result=dict(machine=machine,observations=rows,limitation='Sampled fields only; labels describe attempted input, not verified reached views. Null palette comparison means not measured. Empty yellow list does not prove no glitch.')
 (root/'palette-report.json').write_text(json.dumps(result,indent=2))
 print(root.name,len(rows),'frames',sum(x['instructions'] for x in rows),'instructions',dict(sum((collections.Counter(x['palette_calls']) for x in rows),collections.Counter())))
 return result
if __name__=='__main__':
 for arg in sys.argv[1:]:report(Path(arg))
