"""Contact sheet of retained regression images for visual review."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(sys.argv[1]);cpu=sys.argv[2];kind=sys.argv[3] if len(sys.argv)>3 else 'flight'
paths=sorted(root.glob(cpu+'-*/'+('flight.png' if kind=='flight' else 'startup-*.png')))
paths=[p for p in paths if 'rejected' not in p.parent.name]
assert paths
im=Image.new('RGB',(1120,190*((len(paths)+3)//4)));d=ImageDraw.Draw(im)
for i,p in enumerate(paths):
 t=Image.open(p);t.thumbnail((280,166));x=(i%4)*280;y=(i//4)*190;im.paste(t,(x,y+20));d.text((x+5,y+4),p.parent.name+(' '+p.stem.split('-')[-1] if kind!='flight' else ''),fill='white')
out=root.parent/(root.name+'-'+cpu+'-'+kind+'-contact.png');im.save(out);print(out)
