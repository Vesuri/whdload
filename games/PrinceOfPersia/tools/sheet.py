#!/usr/bin/env python3
"""Contact sheet: sheet.py OUT.png COLS IMG... (labels each tile with its file stem)"""
import sys
from pathlib import Path
from PIL import Image,ImageDraw
out,cols,files=sys.argv[1],int(sys.argv[2]),sys.argv[3:]
ims=[Image.open(f).convert('RGB') for f in files];w,h=ims[0].size;w//=2;h//=2
sheet=Image.new('RGB',(cols*w,((len(ims)+cols-1)//cols)*(h+12)),'white');d=ImageDraw.Draw(sheet)
for i,(f,im) in enumerate(zip(files,ims)):
    x,y=(i%cols)*w,(i//cols)*(h+12);sheet.paste(im.resize((w,h)),(x,y+12));d.text((x+2,y),Path(f).stem,fill='black')
sheet.save(out)
