#!/usr/bin/env python3
"""Independent road geometry oracle using the user's captured tables and track.
  subunit_geometry.py ORIGINAL/render [SUBUNIT/render]
Check the model against original completed rows before measuring held-input
whole-unit crossings. Renderer angles are 8.8: the sine lookup reads their high byte.
No game assets are embedded or written by this tool.
"""
import argparse,json,struct
from pathlib import Path

A=0x7ffe

def signed_word(n):return (n+32768)%65536-32768

def signed_byte(n):return (n+128)%256-128

def project(b,mem,base,n,h,l,f,seed=False,mirror=False):
    word=lambda off:struct.unpack_from('>h',b,A+off)[0]
    long=lambda off:struct.unpack_from('>I',b,A+off)[0]
    def attr(segment):
        kind=mem[long(-13148)-base+segment]&127
        offset=long(-13152)-base+4*kind
        return signed_byte(mem[offset+1]),signed_byte(mem[offset+2])
    sine=lambda angle:word(-26166+2*signed_byte(angle>>8))
    partial=lambda v:(v*(f>>1))>>15
    angle_partial=lambda v:(v*(f>>1)+16384)>>15
    wrap=signed_word
    height,slope=83,0
    heading=wrap(-h) if mirror else h
    lateral=wrap(-l)
    if mirror:lateral>>=1
    if seed:
        curve,hill=attr(n+1)
        if mirror:
            heading=wrap(heading+angle_partial(2*curve))
            slope=wrap(slope-angle_partial(hill))
            height=wrap(height+partial(sine(slope)))
            lateral=wrap(lateral+partial(sine(heading)))
        else:
            heading=wrap(heading-angle_partial(2*curve))
            slope=wrap(slope+angle_partial(hill))
            height=wrap(height-partial(sine(wrap(slope-hill))))
            lateral=wrap(lateral-partial(sine(wrap(heading+2*curve))))
    result=[]
    for k in range(24 if mirror else 44):
        curve,hill=attr(n-k if mirror else n+1+k)
        slope=wrap(slope-hill);height=wrap(height+sine(slope))
        heading=wrap(heading+2*curve);lateral=wrap(lateral+sine(heading))
        ht,lt=(-26968,-27018) if mirror else (-26780,-26870)
        hs,ls=word(ht+2*k),word(lt+2*k)
        if k and (not mirror or k<23):
            neighbour=k+1 if mirror else k-1
            hs+=partial(word(ht+2*neighbour)-hs)
            ls+=partial(word(lt+2*neighbour)-ls)
        y=(height*hs>>16)+(29 if mirror else 76)
        x=(lateral*ls*2>>16)+(280 if mirror else 125)
        result.append((wrap(x),wrap(y)))
    return result

def validate(path,subunit=False):
    meta=json.loads((path/'metadata.json').read_text())
    mem=(path/'assets.bin').read_bytes();base=meta['assets_base']
    for view in ('main','mirror'):
        mismatch=0;total=0;jumps=[[],[]]
        for file in sorted(path.glob(f'{view}-*.bin')):
            b=file.read_bytes();word=lambda off:struct.unpack_from('>h',b,A+off)[0]
            n,h,l=word(-13394),word(-13388),word(-13382)
            fraction=struct.unpack_from('>H',b,A-13392)[0] if subunit else 0
            actual=[(word(-5702+52*k+10),word(-5702+52*k+12)) for k in range(24 if view=='mirror' else 44)]
            ref=project(b,mem,base,n,h,l,fraction,subunit,view=='mirror')
            mismatch+=ref!=actual;total+=1
            after=project(b,mem,base,n+1,h,l,0,mirror=view=='mirror')
            for seed in (False,True):
                before=project(b,mem,base,n,h,l,65535,seed,view=='mirror')
                pairs=((k,k+1) for k in range(1,23)) if view=='mirror' else ((k,k-1) for k in range(1,44))
                jumps[seed]+=[max(abs(a-z) for a,z in zip(before[k],after[j])) for k,j in pairs]
        print(path,view,f'geometry mismatches {mismatch}/{total}; held-input crossing max (unseeded/seeded):',*[max(v,default=0) for v in jumps],'; >1 px:',*[sum(x>1 for x in v) for v in jumps])
        assert total and not mismatch,'model must reproduce completed rows before interpreting its predictions'
        assert max(jumps[1])<=1,'fractional segment seed still has a boundary discontinuity'

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('original',type=Path);p.add_argument('subunit',type=Path,nargs='?')
    a=p.parse_args();validate(a.original)
    if a.subunit:validate(a.subunit,True)
