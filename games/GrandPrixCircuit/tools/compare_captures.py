#!/usr/bin/env python3
"""Compare fresh boots without ignoring arbitrary game state or trace differences."""
import argparse,hashlib,io,json
from pathlib import Path
from PIL import Image,ImageChops
import _amigaxdev
from amigaxdev import barto
from compare_state import differences,DATA
p=argparse.ArgumentParser();p.add_argument('a',type=Path);p.add_argument('b',type=Path);a=p.parse_args()
ma,mb=[json.loads((x/'metadata.json').read_text()) for x in (a.a,a.b)];assert ma['slave_sha256']==mb['slave_sha256']
fail=[]
for name in ('before.bin','code.bin'):
 x,y=[(root/name).read_bytes()[m['data_base']-m['base']:m['data_base']-m['base']+DATA] for root,m in ((a.a,ma),(a.b,mb))]
 ds=differences(x,y,ma,mb)
 print(name,'whole-data differences',len(ds),ds[:20])
 if ds:fail.append(name)
x,y=[barto.load(root/'trace.bin') for root in (a.a,a.b)];assert len(x.fields)==len(y.fields)
counts={'instructions':0,'dma':0,'active_pixels':0}
for f,g in zip(x.fields,y.fields):
 if bytes(x.data[f.insn_off:f.insn_end])!=bytes(y.data[g.insn_off:g.insn_end]):counts['instructions']+=1
 if f.dma!=g.dma:counts['dma']+=1
 X,Y=[Image.open(io.BytesIO(s)).convert('RGB').crop((74,36,714,436)) for s in (f.shot,g.shot)]
 if ImageChops.difference(X,Y).getbbox():counts['active_pixels']+=1
print('different fields:',counts)
assert not fail and not any(counts.values()),(fail,counts)
print('PASS: whole data at both boundaries, every instruction/register/cycle record, DMA record and active pixel identical')
