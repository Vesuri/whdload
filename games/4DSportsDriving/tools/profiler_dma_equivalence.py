#!/usr/bin/env python3
"""Compare recorded display activity with/without the private MMU event recorder."""
import argparse,json,hashlib,io
from PIL import Image,ImageChops
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('reference',type=Path);a=p.parse_args()
t=barto.load(a.capture/'trace.bin');old=barto.load(a.reference/'trace.bin')
assert len(t.fields)==len(old.fields)==250
assert (a.capture/'capture.json').read_bytes()==(a.reference/'capture.json').read_bytes()
pixel_bounds=[]
diff={key:[] for key in ('dma','custom','screenshot','screenshot_pixels','cycles')}
for f,g in zip(t.fields,old.fields):
 if f.dma_size!=g.dma_size or f.dma!=g.dma:diff['dma'].append(f.index)
 if f.custom!=g.custom:diff['custom'].append(f.index)
 if f.shot_kind!=g.shot_kind or f.shot!=g.shot:
  diff['screenshot'].append(f.index)
  x=Image.open(io.BytesIO(f.shot)).convert('RGBA');y=Image.open(io.BytesIO(g.shot)).convert('RGBA')
  if x.size!=y.size or x.tobytes()!=y.tobytes():
   diff['screenshot_pixels'].append(f.index)
   pixel_bounds.append([f.index,ImageChops.difference(x,y).convert('RGB').getbbox() if x.size==y.size else None])
 if f.cycles!=g.cycles:diff['cycles'].append(f.index)
r=dict(fields=250,differing_fields=diff,screenshot_difference_bounds=pixel_bounds,reference=str(a.reference),same_starting_slave_and_state='see profiler-equivalence.json',scope='Paired capture display and field-cycle comparison, including part boundaries; not proof of per-instruction timing accuracy or all emulator behavior.')
(a.capture/'profiler-dma-equivalence.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(fields=250,differing_field_counts={k:len(v) for k,v in diff.items()},unique_pixel_difference_bounds=sorted(set(tuple(v) for _,v in pixel_bounds if v))),indent=2))
