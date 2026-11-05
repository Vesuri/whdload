#!/usr/bin/env python3
"""Summarise aprof_run.py output: aprof_report.py WINDOW.prof MEMDIR [FIELDS|-] [MIN%]

FIELDS defaults to the VBL-counter delta in clocks.txt beside the profile.

Frames = completed swaps at +044CA; time shares are of all profiled clock units
(STOP included as exec's idle PC). The tree is aprof's structural JSR/BSR/exception tree.
"""
import bisect,collections,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev import aprof
from report import region,starts,use_layout,REGIONS
prof,memdir=sys.argv[1:3];FIELDS=int(sys.argv[3]) if len(sys.argv)>3 and sys.argv[3]!='-' else None
ck=os.path.join(os.path.dirname(prof),'clocks.txt')
if FIELDS is None and os.path.exists(ck):
    # The game's VBL counter: `monitor fields N` also finishes the field it starts in.
    import ast
    c0,c1=[ast.literal_eval(l.split(' ',1)[1]) for l in open(ck).read().splitlines()]
    FIELDS=c1['vbl']-c0['vbl'];TICKS=c1['tick']-c0['tick']
else:TICKS=None
FIELDS=FIELDS or 500
MIN=float(sys.argv[4]) if len(sys.argv)>4 else 0.5
use_layout(memdir);mem=open(os.path.join(memdir,'fast.bin'),'rb').read()
h,pcs,nodes=aprof.parse_profile(open(prof).read())
tot=h['units'];g=REGIONS[0][1]
def nm(pc):
    r,o=region(pc)
    if r=='gamemule':return f'+{o:05x}'
    if r=='kick13':return f'ROM ${0xfc0000+o:06x}'
    return f'{r} ${pc:06x}'
frames=pcs.get(g+0x44ca,(0,0))[1]
stop=sum(v[0] for pc,v in pcs.items() if region(pc)==('kick13',0xf90))
print(f'{prof}: {frames} frames in {FIELDS} fields = {50*frames/FIELDS:.1f} fps; STOP idle {100*stop/tot:.1f}%; '
      f'chip-bus share of units {100*sum(v[2] for v in pcs.values())/tot:.1f}%')
reg=collections.Counter()
for pc,v in pcs.items():reg[region(pc)[0]]+=v[0]
if TICKS is not None:print(f'simulation ticks {TICKS} = {50*TICKS/FIELDS:.2f}/s (game-time speed vs A500 reference 2.7/s: {50*TICKS/FIELDS/2.7:.1f}x)')
print('by region:',', '.join(f'{k} {100*c/tot:.1f}%' for k,c in reg.most_common()))
fs=starts(mem,'gamemule');fn=collections.Counter();chip=collections.Counter()
for pc,v in pcs.items():
    r,o=region(pc)
    if r=='gamemule':k=fs[bisect.bisect_right(fs,o)-1]
    elif r=='kick13':k=('rom',o&~0xff)
    else:k=(r,pc&~0xff)
    fn[k]+=v[0];chip[k]+=v[2]
print('top self (function start; ROM by page) with chip-bus wait share:')
for k,c in fn.most_common(30):
    n=f'+{k:05x}' if isinstance(k,int) else (f'ROM ${0xfc0000+k[1]:06x}' if k[0]=='rom' else f'{k[0]} ${k[1]:06x}')
    print(f'  {n:14s} {100*c/tot:6.2f}%  chip {100*chip[k]/max(c,1):5.1f}%')
children,order,incl=aprof.call_tree(nodes)
print(f'call tree (inclusive >= {MIN}%):')
def walk(n,ind):
    for c in sorted(children[n],key=lambda c:-incl[c]):
        if 100*incl[c]/tot<MIN:continue
        p,t,kind,selfu,calls=nodes[c]
        lab=nm(t) if kind==0 else f'vector {kind} -> {nm(t)}'
        print(f'  {"  "*ind}{lab:28s} {100*incl[c]/tot:6.2f}%  self {100*selfu/tot:5.2f}%  calls/frame {calls/max(frames,1):7.2f}')
        if ind<9:walk(c,ind+1)
walk(0,0)
