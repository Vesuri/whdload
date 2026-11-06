#!/usr/bin/env python3
"""Compare same-named screenshots in two directories: sameshots.py DIR_A DIR_B

Ignores x >= 752: the stub's screenshots leave their last two columns unwritten (host garbage).
Exits 1 if any pair differs or a file is missing on one side."""
import sys
from pathlib import Path
from PIL import Image,ImageChops
a,b=map(Path,sys.argv[1:3]);bad=0
names=sorted({p.name for d in (a,b) for p in d.glob('*.png')})
for n in names:
    if not (a/n).exists() or not (b/n).exists():print('missing',n);bad=1;continue
    x,y=(Image.open(d/n).convert('RGB') for d in (a,b));box=(0,0,min(752,x.width),x.height)
    d=ImageChops.difference(x.crop(box),y.crop(box)).getbbox()
    if d:print('differs',n,d);bad=1
print(f'{len(names)} shots,','all equal' if not bad else 'DIFFERENT');sys.exit(bad)
