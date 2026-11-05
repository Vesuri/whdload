"""Tile PNG snapshots into one image: montage.py OUT COLS IN..."""
import sys
from PIL import Image
out,cols,files=sys.argv[1],int(sys.argv[2]),sys.argv[3:]
ims=[Image.open(f).convert('RGB') for f in files]
w,h=ims[0].size; rows=(len(ims)+cols-1)//cols
m=Image.new('RGB',(cols*w,rows*h))
for i,im in enumerate(ims): m.paste(im,((i%cols)*w,(i//cols)*h))
m.save(out)
