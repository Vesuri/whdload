#!/usr/bin/env python3
"""Compare state at VBL or SOFT sample indices; report mismatches, never pictures.
  compare_state.py OUT_A/state OUT_B/state [--assert-core] [--start N]
Compares the named variables, then every byte of hunk 0 (the game keeps its variables
there), listing the first differing offsets per sample.
"""
import argparse,json
from pathlib import Path
from state_report import VARIABLES,value
def read(p):
    root=Path(p)
    return (root/'initial.bin').read_bytes(),[f.read_bytes() for f in sorted(root.glob('[0-9][0-9][0-9][0-9].bin'))]
def main():
    p=argparse.ArgumentParser();p.add_argument('a');p.add_argument('b');p.add_argument('--assert-core',action='store_true');p.add_argument('--align-director',action='store_true',help='align initial SOFT samples by the demo director counter');p.add_argument('--simulation',action='store_true',help='compare complete car records and published view per SOFT tick');p.add_argument('--driving',action='store_true',help='also compare cockpit camera and player physics; requires --simulation');p.add_argument('--start',type=int,default=0);a=p.parse_args()
    if a.driving and not a.simulation:p.error('--driving requires --simulation')
    ia,aa=read(a.a);ib,bb=read(a.b);n=min(len(aa),len(bb))
    if a.simulation:
        ma=json.loads((Path(a.a)/'metadata.json').read_text())
        mb=json.loads((Path(a.b)/'metadata.json').read_text())
        assert ma.get('sample_at')==mb.get('sample_at')=='soft','requires SOFT captures'
        shift_a=shift_b=0
        if a.align_director:
            matches=[(i,j) for i in range(min(20,len(aa))) for j in range(min(20,len(bb))) if aa[i][0x268d0:0x268d2]==bb[j][0x268d0:0x268d2]]
            assert matches,'no initial director alignment found'
            shift_a,shift_b=min(matches,key=lambda ij:sum(ij))
            aa=aa[shift_a:];bb=bb[shift_b:];n=min(len(aa),len(bb))
            print(f'Director alignment: A +{shift_a}, B +{shift_b}; {n} overlapping ticks')
        else:
            assert len(aa)==len(bb),'capture lengths differ'
        assert n,'no SOFT samples'
        ranges={'cars (33 complete records)':(0x22758,0x2326e),'published view':(0x26664,0x26676),'camera track position':(0x268d2,0x268d4),'director countdown':(0x268d0,0x268d2),'mode':(0x268da,0x268db)}
        if a.driving:
            assert not a.align_director, 'director does not advance in driving mode'
            ranges.update({'cockpit published camera':(0x9834,0x9846),'player physics and dashboard source':(0x9846,0x9b0a)})
            assert all(x[0x268da]==0 and not x[0x9b2e]&2 for x in aa+bb), 'capture left cockpit driving'
        failed=False
        for name,(lo,hi) in ranges.items():
            bad=[i for i,(x,y) in enumerate(zip(aa,bb)) if x[lo:hi]!=y[lo:hi]]
            print(f'{name}: {n-len(bad)}/{n} identical; first mismatches {bad[:8]}')
            if bad:
                i=bad[0];offs=[o for o in range(lo,hi) if aa[i][o]!=bb[i][o]]
                print('  first offsets: '+', '.join(f'game:{o:05x}' for o in offs[:16]))
            failed |= bool(bad)
        for name in ('hunk1','hunk2','hunk5'):
            bad=[]
            for i in range(n):
                x=(Path(a.a)/f'{i+shift_a:04d}-{name}.bin').read_bytes()
                y=(Path(a.b)/f'{i+shift_b:04d}-{name}.bin').read_bytes()
                if x!=y:bad.append(i)
            print(f'{name} (whole BSS, includes renderer data): {n-len(bad)}/{n} identical')
            if a.driving and name=='hunk5':failed |= bool(bad)
        if failed: raise SystemExit('Simulation equivalence failed; do not enable smoothing')
        print('Named simulation ranges identical; this alone does not prove all simulation state')
        return
    if not n: p.error('both directories must contain VBL samples')
    print(f'Comparing {n} VBL samples (indices 0..{n-1}); lengths={len(aa)}/{len(bb)}')
    for name,v in VARIABLES.items():
        initial=(value(ia,*v),value(ib,*v));bad=[i for i,(x,y) in enumerate(zip(aa,bb)) if value(x,*v)!=value(y,*v)]
        print(f'{name}: initial={initial}, match={n-len(bad)}/{n}, first mismatches='+str([(i,value(aa[i],*v),value(bb[i],*v)) for i in bad[:8]]))
    print(f'initial hunk 0 identical: {ia==ib}')
    bad=[i for i in range(n) if aa[i]!=bb[i]]
    print(f'whole hunk 0: match={n-len(bad)}/{n}')
    for i in bad[:5]:
        offs=[o for o in range(min(len(aa[i]),len(bb[i]))) if aa[i][o]!=bb[i][o]]
        print(f'  sample {i}: {len(offs)} bytes differ, first at '+', '.join(f'game:{o:05x}' for o in offs[:10]))
    if a.assert_core:
        assert len(aa)==len(bb), 'capture lengths differ'
        failures=[i for i in range(a.start,n) if aa[i]!=bb[i]]
        assert not failures, f'hunk 0 differs at samples {failures[:8]}'
        print(f'hunk 0 identical at samples {a.start}..{n-1}')
if __name__=='__main__':main()
