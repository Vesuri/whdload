#!/usr/bin/env python3
"""Compare raw state at identical VBL sample indices; report mismatches, never pictures.
  compare_state.py OUT_A/state OUT_B/state
An isolated mismatch can be an interrupt inside the demo's borrowed-state transaction.
Inspect the corresponding PC/commit writer before assigning a gameplay interpretation.
"""
import argparse
from pathlib import Path
from state_report import VARIABLES,value
CORE={'distance','speed','clock','opponent_distance','opponent_speed','traffic_forward',
      'traffic_oncoming','rpm','fuel','animation_1','animation_2','engine_period','road_length','stage','rng'}
def read(p):
    root=Path(p)
    return (root/'initial.bin').read_bytes(),[f.read_bytes() for f in sorted(root.glob('[0-9][0-9][0-9][0-9].bin'))]
def main():
    p=argparse.ArgumentParser();p.add_argument('a');p.add_argument('b');a=p.parse_args()
    ia,aa=read(a.a);ib,bb=read(a.b);n=min(len(aa),len(bb))
    if not n: p.error('both directories must contain VBL samples')
    print(f'Comparing {n} VBL samples (indices 0..{n-1}); lengths={len(aa)}/{len(bb)}')
    for name,v in VARIABLES.items():
        initial=(value(ia,*v),value(ib,*v));bad=[i for i,(x,y) in enumerate(zip(aa,bb)) if value(x,*v)!=value(y,*v)]
        kind='core' if name in CORE else 'sampled/visual/field-counter'
        print(f'{name} [{kind}]: initial={initial}, match={n-len(bad)}/{n}, first mismatches='+str([(i,value(aa[i],*v),value(bb[i],*v)) for i in bad[:8]]))
    # Boot lengths differ; compare field-clock/deadline phases relative to sample 0.
    va=value(aa[0],*VARIABLES['vbl']);vb=value(bb[0],*VARIABLES['vbl'])
    for name in ('vbl','deadline'):
        v=VARIABLES[name]
        bad=[i for i,(x,y) in enumerate(zip(aa,bb)) if (value(x,*v)-va)&0xffffffff != (value(y,*v)-vb)&0xffffffff]
        print(f'{name} relative to first VBL: match={n-len(bad)}/{n}, first mismatches={bad[:8]}')
if __name__=='__main__':main()
