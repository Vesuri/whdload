#!/usr/bin/env python3
"""Contact sheet: python3 tools/sheet.py OUT.png A.png B.png ... (quarter size, labelled, 5 across)."""
import sys
from pathlib import Path
from PIL import Image,ImageDraw
out,files=sys.argv[1],sys.argv[2:]
ims=[Image.open(f).convert('RGB') for f in files];w,h=ims[0].width//2,ims[0].height//2;cols=min(5,len(ims))
s=Image.new('RGB',(w*cols,h*((len(ims)+cols-1)//cols)))
for k,(f,im) in enumerate(zip(files,ims)):
    x,y=(k%cols)*w,(k//cols)*h;s.paste(im.resize((w,h)),(x,y));ImageDraw.Draw(s).text((x+4,y+4),Path(f).stem,fill=(255,255,0))
s.save(out)
