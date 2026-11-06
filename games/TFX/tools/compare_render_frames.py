"""Compare published plane bytes separately from emulator display output."""
import sys,struct,json
from pathlib import Path
from replay_flight import ROOT
from amigaxdev import barto
from PIL import Image
left,right=map(Path,sys.argv[1:3]);result={}
for n in [1,10,30,45,57]:
 planes=[];rgb=[]
 for p in [left,right]:
  t=barto.load(p/f'swap-{n:03d}.trace');f=t.fields[-1];first={}
  for o in range(0,len(f.dma),f.dma_size):
   if struct.unpack_from('<h',f.dma,o+29)[0]==6:first.setdefault(struct.unpack_from('<H',f.dma,o)[0],struct.unpack_from('<I',f.dma,o+12)[0])
  bases=[first[0x110+2*i] for i in range(8)];planes.append(b''.join(t.chip[a:a+8000] for a in bases));rgb.append(Image.open(p/f'swap-{n:03d}.png').convert('RGB').tobytes())
 offsets=[i for i,(a,b) in enumerate(zip(*planes)) if a!=b]
 result[n]=dict(planes_equal=planes[0]==planes[1],different_plane_bytes=len(offsets),first_different_offsets=offsets[:20],rgb_equal=rgb[0]==rgb[1])
print(json.dumps(result,indent=2))
