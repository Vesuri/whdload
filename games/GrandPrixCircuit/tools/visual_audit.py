import sys,struct,io,json
from pathlib import Path
from PIL import Image,ImageChops
import _amigaxdev
from amigaxdev import barto
p=Path(sys.argv[1]);t=barto.load(p/'trace.bin');last=None;changed=[]
for f in t.fields:
 display=next(struct.unpack_from('<I',f.dma,o+12)[0] for o in range(0,len(f.dma),f.dma_size) if f.dma[o+29]==6 and struct.unpack_from('<H',f.dma,o)[0]==0x110)
 im=Image.open(io.BytesIO(f.shot)).convert('RGB').crop((74,112,714,184))
 if last and display==last[0]:
  diff=ImageChops.difference(im,last[1]);box=diff.getbbox()
  if box:
   changed.append({'previous':f.index-1,'field':f.index,'horizon_bbox':box})
   if len(changed)==1:
    (p/'horizon-before.png').write_bytes(t.fields[f.index-1].shot)
    (p/'horizon-after.png').write_bytes(f.shot)
 last=(display,im)
r={'fields':len(t.fields),'horizon_changes_without_buffer_change':changed}
(p/'visual-audit.json').write_text(json.dumps(r,indent=2)+'\n');print(p.name,len(changed),changed[:4])
