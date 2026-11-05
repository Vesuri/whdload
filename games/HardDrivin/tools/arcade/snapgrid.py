"""Tile a run's snapshots at half size: snapgrid.py RUN_DIR [COLS]"""
import sys,glob
from PIL import Image
run=sys.argv[1]; cols=int(sys.argv[2]) if len(sys.argv)>2 else 5
fs=sorted(glob.glob(run+'/snap/harddriv/*.png'))
ims=[Image.open(f).convert('RGB').resize((254,192)) for f in fs]
rows=(len(ims)+cols-1)//cols
m=Image.new('RGB',(cols*254,rows*192))
for i,im in enumerate(ims): m.paste(im,((i%cols)*254,(i//cols)*192))
m.save(run+'/grid.png'); print(len(fs),'snaps ->',run+'/grid.png')
