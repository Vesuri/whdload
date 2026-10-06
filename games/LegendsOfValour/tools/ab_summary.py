#!/usr/bin/env python3
"""Summarise tools/ab_window.sh captures: slave hash, fps, C2P/render cycles, game state and
off/on screenshot comparison per route and machine; writes PREFIX-ROUTE-MACHINE-comparison.png.
  python3 tools/ab_summary.py PREFIX        e.g. w2
"""
from pathlib import Path
import json,re,hashlib,sys
from PIL import Image,ImageDraw,ImageChops
root=Path('tmp/prof'); prefix=sys.argv[1]
for route,machine in [('spin','a500'),('spin','a1200'),('wall','a500'),('wall','a1200'),('wall','68000-fast')]:
 dirs=[root/f'{prefix}-{route}-{machine}-{mode}' for mode in ('off','on')]
 if not all((p/'state.json').exists() for p in dirs): continue
 print('\n',route,machine)
 for p in dirs:
  print(p.name,hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest())
  print(re.search(r'\d+ frames in .*fps \(PAL\)',(p/'frames.txt').read_text())[0])
  print((p/'c2p.txt').read_text().splitlines()[1:4]); print((p/'render.txt').read_text().strip())
 states=[json.loads((p/'state.json').read_text()) for p in dirs]
 print('headings',*[s['heading'] for s in states],'movement steps',*[s['movement_step'] for s in states])
 print('same pose',[(s['player_x'],s['player_y']) for s in states], 'same objects',states[0]['objects']==states[1]['objects'])
 sheet=Image.new('RGB',(1508,1192),'white');d=ImageDraw.Draw(sheet); crops=[]
 for row,when in enumerate(('first','last')):
  ims=[]
  for col,mode in enumerate(('off','on')):
   im=Image.open(dirs[col]/f'{when}.png').convert('RGB');ims.append(im)
   crop=im.crop((202,68,586,252)); crops.append(crop)
   sheet.paste(im,(754*col,596*row+20));d.text((754*col+10,596*row+3),f'{machine} {prefix} {mode}: {when}',fill='black')
  print(when,'whole screenshot identical:',ImageChops.difference(*ims).getbbox() is None)
 sheet.save(root/f'{prefix}-{route}-{machine}-comparison.png')
 print('all four viewports identical:',all(ImageChops.difference(crops[0],im).getbbox() is None for im in crops[1:]))
