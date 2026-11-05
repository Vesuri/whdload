#!/usr/bin/env python3
"""Where the time goes in a flight_profile reduction: report.py PROFILE MEMDIR [N]

PROFILE: profile.pkl.gz; MEMDIR: dump_start.py output (fast.bin at $200000).
Region bases come from MEMDIR/layout.json (layout.py); the defaults are the a500-fast run's. gamemule offsets are hunk-0 offsets, the slave's patch-list numbering.
"""
import bisect,collections,os,struct,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import _amigaxdev  # noqa: F401
from amigaxdev.callprofile import Reduction
FAST=0x200000
REGIONS=[('gamemule',0x985cd8,0xf0c8),('kick13',0x935000,0x40000),('Gunship',0x9802b0,0x1c68)]
def use_layout(memdir):
    """Take the region bases from MEMDIR/layout.json (layout.py) when it exists."""
    import json
    p=os.path.join(memdir,'layout.json')
    if os.path.exists(p):
        L=json.load(open(p));REGIONS[:]=[('gamemule',L['gamemule'],0xf0c8),('kick13',L['kick13'],0x40000),('Gunship',L['launcher'],0x1c68)]

def region(pc):
    for n,b,l in REGIONS:
        if b<=pc<b+l:return n,pc-b
    return 'other',pc

def starts(mem,name):
    """Function starts in a code region: link a5 prologues and static jsr/bsr targets."""
    n,b,l=[r for r in REGIONS if r[0]==name][0]
    code=mem[b-FAST:b-FAST+l];s=set()
    for o in range(0,l-6,2):
        w=struct.unpack('>H',code[o:o+2])[0]
        if w==0x4e55:s.add(o)                                   # link a5,#
        elif w==0x4eb9:                                        # jsr abs.l
            t=struct.unpack('>I',code[o+2:o+6])[0]-b
            if 0<=t<l:s.add(t)
        elif w==0x4eba:                                        # jsr d16(pc)
            t=o+2+struct.unpack('>h',code[o+2:o+4])[0]
            if 0<=t<l:s.add(t)
        elif w&0xff00==0x6100:                                 # bsr
            d=w&0xff
            t=o+2+(struct.unpack('>h',code[o+2:o+4])[0] if d==0 else (d-256 if d>127 else d))
            if 0<=t<l:s.add(t)
    return sorted(s)

def main():
    use_layout(sys.argv[2]);r=Reduction.load(sys.argv[1]);mem=open(os.path.join(sys.argv[2],'fast.bin'),'rb').read()
    N=int(sys.argv[3]) if len(sys.argv)>3 else 40
    tot=r.total();print(f'traced cycles {tot}  fields {len(r.fields)}  ({tot/len(r.fields):.0f}/field)')
    reg=collections.Counter()
    for pc,c in r.self.items():reg[region(pc)[0] if isinstance(pc,int) else 'gap']+=c
    print('\nself cycles by region:')
    for n,c in reg.most_common():print(f'  {n:10s} {100*c/tot:6.2f}%')
    fs={n:starts(mem,n) for n in ('gamemule','Gunship')}
    fn=collections.Counter();ex=collections.Counter()
    for pc,c in r.self.items():
        if not isinstance(pc,int):continue
        n,o=region(pc)
        if n in fs and fs[n]:
            i=bisect.bisect_right(fs[n],o)-1;key=(n,fs[n][i] if i>=0 else 0)
        elif n=='kick13':key=(n,(o&~0xff))
        else:key=(n,pc&~0xff)
        fn[key]+=c;ex[key]+=r.counts[pc]
    print(f'\ntop {N} functions by self cycles (kick13/other grouped by 256-byte page):')
    for (n,o),c in fn.most_common(N):
        extra=f'  ROM ${0xfc0000+o:06x}' if n=='kick13' else ''
        print(f'  {n:9s} +{o:05x} {100*c/tot:6.2f}%  {c/len(r.fields):8.0f} cyc/field{extra}')
if __name__=='__main__':main()
