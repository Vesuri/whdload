"""Decode a captured four-plane 320x200 front buffer for evidence review."""
from pathlib import Path
import sys,struct
from PIL import Image
p=Path(sys.argv[1]);chip=(p/'anchor-chip.bin').read_bytes()
for field in map(int,sys.argv[2:]):
 b=(p/f'state-{field:05d}.bin').read_bytes();palptr=struct.unpack_from('>I',b,0x7100-0x7036)[0]
 colors=struct.unpack_from('>16H',chip,palptr);pal=[tuple(((c>>s)&15)*17 for s in [8,4,0]) for c in colors]
 planes=(p/f'front-{field:05d}.bin').read_bytes();im=Image.new('RGB',(320,200));px=im.load()
 for y in range(200):
  for x in range(320):
   idx=sum(((planes[k*8000+y*40+x//8]>>(7-x%8))&1)<<k for k in range(4));px[x,y]=pal[idx]
 im.resize((640,400),Image.Resampling.NEAREST).save(p/f'view-{field:05d}.png')
 print(p/f'view-{field:05d}.png')
