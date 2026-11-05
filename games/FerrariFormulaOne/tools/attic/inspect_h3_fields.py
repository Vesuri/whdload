from pathlib import Path
import sys,io,json
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
from PIL import Image,ImageChops
p=Path('tmp/dev/tmp/step5/c4-q03-render-profile-a1200-fast-h3-matched-candidate');t=barto.load(p/'detail.bin');images=[]
for i in [0,1,2,3]:
 f=t.fields[i];print(i,f.shot_kind,len(f.shot));im=Image.open(io.BytesIO(f.shot)).convert('RGB');im.save(p/f'field-{i}.png');images.append(im)
for i in [1,2]:
 diff=ImageChops.difference(images[0],images[i]);print(i,diff.getbbox());diff.save(p/f'diff-0-{i}.png')
