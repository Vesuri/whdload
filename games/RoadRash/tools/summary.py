#!/usr/bin/env python3
"""Summarise a reduced profile: python3 tools/summary.py OUT/profile.pkl.gz [N]
Field totals, DMA slot shares, self cycles per routine (nearest preceding traced call target),
inclusive top routines and the call tree. Routine names are addresses (the game is at $80000+)."""
import bisect,collections,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.callprofile import Reduction
r=Reduction.load(sys.argv[1]);N=int(sys.argv[2]) if len(sys.argv)>2 else 25
F=r.fields;nf=len(F);tot=r.total() or 1
print(f'{nf} fields; per field: {sum(f["cycles"] for f in F)/nf:.0f} cycles, traced CPU {tot/nf:.0f}, '
      f'no-PC {sum(f["nopc"] for f in F)/nf:.0f}, exception gaps {sum(f["gap"] for f in F)/nf:.0f}, idle {sum(f["idle"] for f in F)/nf:.0f}')
print('DMA slots: '+', '.join(f'{k} {v*100:.1f}%' for k,v in r.dma_shares().items()))
starts=sorted({fr for st in r.stacks for fr in st if isinstance(fr,int)}|{fr[1] for st in r.stacks for fr in st if isinstance(fr,tuple)})
selfr=collections.Counter()
for pc,c in r.self.items():
    i=bisect.bisect_right(starts,pc)-1;selfr[starts[i] if i>=0 else 0]+=c
print(f'\nself cycles by routine (top {N}):')
for a,c in selfr.most_common(N):print(f'  {a:08x}  {c/tot*100:6.2f}%')
print(f'\nhottest PCs (top {N}):')
for a,c in r.self.most_common(N):print(f'  {a:08x}  {c/tot*100:6.2f}%  x{r.counts[a]}')
print('\ncall tree (>=1%):');print(r.tree(label=lambda a:f'{a:08x}'))
