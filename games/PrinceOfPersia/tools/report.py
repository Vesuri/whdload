#!/usr/bin/env python3
"""Summarise a profile_run.py capture: report.py PROF [TOP]"""
import collections,sys
from prof import load
red,meta,label=load(sys.argv[1]);TOP=int(sys.argv[2]) if len(sys.argv)>2 else 30
F=red.fields;n=len(F);tot=red.total()
print(f'fields {n} ({n/50:.1f} s PAL), CPU cycles {tot} ({tot/n:.0f}/field)')
print(f"exception-entry gaps {sum(f['gap'] for f in F)/tot*100:.2f}%  STOP/no-PC {sum(f['nopc'] for f in F)/tot*100:.2f}%")
reg=collections.Counter()
for pc,c in red.self.items():reg[label(pc).split(':')[0]]+=c
print('self by region:',', '.join(f'{k} {v/tot*100:.1f}%' for k,v in reg.most_common()))
print('DMA slots:',', '.join(f'{k} {v*100:.1f}%' for k,v in red.dma_shares().items()))
print(f'\nTop {TOP} instructions (self):')
for pc,c in red.self.most_common(TOP):print(f'  {label(pc):16} {c/tot*100:6.2f}%  {red.counts[pc]/n:8.1f} execs/field')
