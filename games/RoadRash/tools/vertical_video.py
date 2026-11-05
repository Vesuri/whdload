from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json
out=Path('tmp/vertical-video');frames=sorted(out.glob('frame-*.png'));rows=[]
canvas=Image.new('RGB',(5*354,10*210),'#202020');draw=ImageDraw.Draw(canvas)
for i,p in enumerate(frames):
 im=Image.open(p).convert('RGB');a=np.array(im);roi=a[200:570,900:1040].astype(int)
 mask=(roi[:,:,0]>125)&(roi[:,:,0]>roi[:,:,1]*1.8)&(roi[:,:,0]>roi[:,:,2]*1.8)
 yy,xx=np.where(mask);y=int(yy.min()+200)
 rows.append(dict(frame=i+1,helmet_y=y))
 thumb=im.crop((0,140,1770,1080)).resize((354,188));x=(i%5)*354;top=(i//5)*210;canvas.paste(thumb,(x,top+22));draw.text((x+5,top+4),f'{i+1:02d}  helmet y={y}',fill='white')
canvas.save(out/'50-frames.jpg');(out/'positions.json').write_text(json.dumps(rows,indent=2));print(rows)
