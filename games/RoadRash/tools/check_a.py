#!/usr/bin/env python3
"""Run a bounded A-series baseline/checkpoint probe (outputs never overwrite a reference)."""
import argparse,json,os
from harness_a import *

def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--fields',type=int,default=500)
    ap.add_argument('--normal',action='store_true');ap.add_argument('--hash',action='store_true')
    args=ap.parse_args()
    if args.fields<500 or args.fields%2:raise ValueError('fields must be even and at least 500')
    slave=Path(os.environ.get('SLAVE',ROOT/'tmp/build'/('RoadRash.slave' if args.normal else 'RoadRash-verify-hash.slave' if args.hash else 'RoadRash-verify.slave'))).resolve()
    os.environ['SLAVE']=str(slave)
    out=Path(args.out)
    if (out/'result.json').exists():raise RuntimeError('choose a fresh output directory')
    s=Session(out)
    try:
        initial=route(s);address=None if args.normal else stats_address(s);before=None if args.normal else counters(s,address)
        print('settled',initial['field'],initial['state_sha256'],flush=True)
        if args.hash:
            if args.normal:raise ValueError('hash requires VERIFY')
            if rd(s,address+48)!=590:raise RuntimeError('hash run requires VERIFY_HASH_FIELD=590; this debugger silently ignores memory writes')
        s.input('JOY2_UP',1)
        rotations=[0xa723c,0xa7240,0xa7244];previous=rotations.index(rd(s,0xa726e));frames=0
        deltas=[]
        for target in range(102,101+args.fields,2):
            if target in (590,100+args.fields):
                s.shot(f'race-{target:04d}.png')
                if field(s)!=target:raise RuntimeError('screenshot field boundary mismatch')
            else:advance(s,target)
            current=rotations.index(rd(s,0xa726e));frames+=(current-previous)%3;previous=current
            deltas.append(rd(s,0xa6f00,2))
            if target==590:distance=snapshot(s)
        end=snapshot(s);after=None if args.normal else counters(s,address)
        histogram=None if args.normal else [y-x for x,y in zip(before['histogram'],after['histogram'])]
        if after and frames!=after['frames']-before['frames']:raise RuntimeError('counter disagrees with independent record-rotation count')
        if args.hash and after['hash_field']!=590:raise RuntimeError(f'hash request not serviced: {after}')
        if os.environ.get('RR_EXPECT_MMU','0')!='0' and (not after or not after['flags']&1 or not after['mmu_tc']&0x8000):raise RuntimeError('MMU run did not prove enabled TC translation')
        result=dict(provenance=provenance(slave,s),initial=initial,at490=distance,end=end,
                    before=before,after=after,histogram=histogram,
                    instrumented=not args.normal,hash_requested=args.hash,rotation_frames=frames,sampled_deltas=deltas,
                    fps=frames*50/(end['field']-initial['field']),
                    distance490=distance['position']-initial['position'])
        if os.environ.get('RR_B'):result['b_stats']=b_counters(s)
        (s.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print('fps',result['fps'],'distance490',result['distance490'],flush=True)
    finally:s.quit()

if __name__=='__main__':main()
