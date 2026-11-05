#!/usr/bin/env python3
"""Contact sheet of the f*.png shots in DIR: sheet.py DIR [COLUMNS]."""
import glob,os,sys
from PIL import Image
d=sys.argv[1];W=int(sys.argv[2]) if len(sys.argv)>2 else 6
fs=sorted(glob.glob(os.path.join(d,'f*.png')));ims=[Image.open(f).convert('RGB').resize((376,284)) for f in fs]
H=(len(ims)+W-1)//W;S=Image.new('RGB',(376*W,284*H))
for i,im in enumerate(ims):S.paste(im,((i%W)*376,(i//W)*284))
S.save(os.path.join(d,'sheet.png'))
