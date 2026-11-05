#!/usr/bin/env python3
"""Text report of attrib.py output: report_attrib.py ATTRIB.pkl [DEPTH] [MIN%]"""
import collections,os,pickle,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from report import region
d=pickle.load(open(sys.argv[1],'rb'));DEPTH=int(sys.argv[2]) if len(sys.argv)>2 else 5
MIN=float(sys.argv[3]) if len(sys.argv)>3 else 0.5
ctx=d['ctx'];tot=sum(ctx.values());nf=len(d['perfield'])
def nm(x):
    if isinstance(x,int):
        r,o=region(x);return f'{r}+{o:05x}' if r!='kick13' else f'ROM ${0xfc0000+o:06x}'
    return str(x)
print(f'{nf} fields, {tot} cycles ({tot/nf:.0f}/field)')
for k,v in ctx.most_common():print(f'  {k:11s} {100*v/tot:6.2f}%')
stop=sum(f.get('stop',0) for f in d['perfield']);print(f'  (STOP idle inside supervisor: {100*stop/tot:.2f}%)')
print('\nsupervisor time by handler entry:')
for h,c in d['sup'].most_common(12):print(f'  {nm(h):24s} {100*c/tot:6.2f}%  {d["supn"][h]/nf:6.1f} entries/field')
print('\nsupervisor self by PC page:')
pg=collections.Counter()
for pc,c in d['supself'].items():r,o=region(pc);pg[(r,o&~0x3f if r!='other' else pc&~0xff)]+=c
for (r,o),c in pg.most_common(12):print(f'  {nm(o+0x935000) if r=="kick13" else r+"+%05x"%o:24s} {100*c/tot:6.2f}%')
# task tree from paths
tree={}
for path,c in d['paths'].items():
    node=tree
    for fr in path[:DEPTH]:
        node=node.setdefault(fr,[0,{}]);node[0]+=c;node=node[1]
print(f'\ntask call tree (inclusive, >= {MIN}% of all cycles, depth {DEPTH}):')
def walk(node,ind):
    for fr,(c,ch) in sorted(node.items(),key=lambda x:-x[1][0]):
        if 100*c/tot<MIN:continue
        print(f'  {"  "*ind}{nm(fr):28s} {100*c/tot:6.2f}%  calls/field {d["calls"][fr]/nf:7.1f}')
        walk(ch,ind+1)
walk(tree,0)
print('\nlibrary calls by inclusive cycles:')
for n,c in sorted(((n,c) for n,c in d['incl'].items() if isinstance(n,str)),key=lambda x:-x[1])[:25]:
    print(f'  {n:24s} {100*c/tot:6.2f}%  calls/field {d["calls"][n]/nf:7.2f}')
