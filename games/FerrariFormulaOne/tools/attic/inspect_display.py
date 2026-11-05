from pathlib import Path
import sys,struct,json,hashlib,collections
from PIL import Image
from io import BytesIO
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
p=Path(sys.argv[1]);t=barto.load(p);rows=[]
for f in t.fields:
 assert f.dma_size==58
 reads=collections.defaultdict(list); writes=[]
 for at in range(0,len(f.dma),58):
  reg,dat,size,addr=struct.unpack_from('<HQHI',f.dma,at);typ=struct.unpack_from('<h',f.dma,at+29)[0]
  if typ==6:reads[reg].append(addr)
  if typ==3 and 0xe0<=reg<0xf8:writes.append([reg,dat])
 im=Image.open(BytesIO(f.shot));h=hashlib.sha256(im.crop((54,36,694,436)).tobytes()).hexdigest()
 rows.append({'field':f.index,'first_dma':{hex(k):hex(v[0]) for k,v in reads.items()},'last_dma':{hex(k):hex(v[-1]) for k,v in reads.items()},'copper_planes':writes[:24],'game_pixels_sha256':h})
 if f.index in (0,8,16,23): (p.parent/f'display-{f.index}.png').write_bytes(f.shot)
print(json.dumps(rows,indent=2))
