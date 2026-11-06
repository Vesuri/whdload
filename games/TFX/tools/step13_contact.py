"""Build labeled contact sheets from retained regression screenshots."""
import sys,math
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
p=Path(__file__).resolve().parents[1]/'tmp/step13';name=sys.argv[1];root=p/name
files=sorted(root.glob('*/flight.png')) if name.startswith('candidate') else sorted(root.glob('*/startup-*.png'))
if not files:raise SystemExit('No screenshots')
w,h=302,252;sheet=Image.new('RGB',(4*w,math.ceil(len(files)/4)*h),'#222222');d=ImageDraw.Draw(sheet)
for i,f in enumerate(files):
 x=i%4*w;y=i//4*h;img=Image.open(f);img.thumbnail((w,h-30));sheet.paste(img,(x,y+30));d.text((x+3,y+4),f.parent.name+' / '+f.stem,fill='white')
sheet.save(p/(name+'-contact.png'));print(len(files),p/(name+'-contact.png'))
