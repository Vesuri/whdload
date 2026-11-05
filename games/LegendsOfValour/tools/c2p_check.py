#!/usr/bin/env python3
"""Read VERIFY pixel-twin evidence from a retained capture (no game bytes emitted)."""
import argparse, os, re, struct
from pathlib import Path
from lov_report import regions
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('capture',type=Path)
p.add_argument('--require-all-views',action='store_true')
p.add_argument('--base',type=lambda x:int(x,0),default=0xc00000)
a=p.parse_args();os.environ['SLAVE']=str(a.capture/'slave.slave')
b=(a.capture/'code.bin').read_bytes();lst=(a.capture/'slave.lst').read_text(errors='replace')
r={n:lo for lo,hi,n,o in regions(b,a.base)}
def sym(n):
    return int(re.search(r'^'+n+r'\s+00:([0-9A-F]{8})\s*(?:EXP)?\s*$',lst,re.M)[1],16)
def read(n,fmt):
    return struct.unpack_from('>'+fmt,b,r['slave']-a.base+sym(n))
print('CPU attention flags:',hex(read('_lov_attnflags','I')[0]))
selected=read('_c2p_function','I')[0]-r['slave']
assert selected in (sym('c2p1x1_4_c5_bm_word'),sym('c2p1x1_4_c5_bm')),'unknown selected converter'
print('converter:', 'word' if selected==sym('c2p1x1_4_c5_bm_word') else 'longword')
print('successful pixel twins:',read('_c2p_tests','I')[0])
assert read('_custom2','I')[0]&1 and read('_custom5','I')[0]&2,'pixel twin was not enabled'
assert read('_c2p_tests','I')[0]>0,'no successful pixel twins'
geometry=read('_c2p_geometries','12H');counts=read('_c2p_counts','3I')
for i in range(3):
    w,h,x,y=geometry[4*i:4*i+4]
    if w:
        print(f'{w} x {h}, origin ({x},{y}): {counts[i]} successful twins')

if a.require_all_views:
    seen={tuple(geometry[4*i:4*i+4]) for i in range(3) if counts[i]}
    assert seen=={(112,64,104,30),(192,92,64,16),(80,48,120,38)},'not all view geometries were verified'
    large=next(counts[i] for i in range(3) if geometry[4*i]==192)
    assert large>=300,'fewer than 300 large-view twins'
