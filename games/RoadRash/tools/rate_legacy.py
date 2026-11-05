#!/usr/bin/env python3
"""Frame rate and game speed in the race: python3 tools/rate.py OUT [SAMPLES]

Goes to the race with drive.to_race (fire until the race hook runs), then holds JOY2_UP for SAMPLES samples (default 250). Each sample is
`monitor fields 1`, which runs 2 fields (stopped at a vsync, the harness counts the stop's
field as partial). Per sample it reads:
  $a726e  per-frame record pointer, rotated by $871dc once per frame through 3 entries:
          frames in the sample = rotation steps mod 3 (at most 2 per 2 fields, as the swap
          waits for a new field)
  $a6f00  the game's delta (fields the last accepted frame took)
  $a5d4c  race field counter (per-field hook, drives the race clock)
  $a5d64  player track position (player record $a5d60 + 4)
Writes OUT/rate.json and race shots. Machine from AMIGA_SETUP (default a1200-fast)."""
import collections,json,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from drive import Session,E,to_race

def rd(s,addr,size):
    r=s.cmd(f'x/1{"w" if size==4 else "h"}x {addr:#x}')
    return int(r.split(':')[1].split()[0],16)

if __name__=='__main__':
    out=sys.argv[1];n=int(sys.argv[2]) if len(sys.argv)>2 else 250
    s=Session(out)
    try:
        to_race(s,E('SETTLE',100))
        rec=[0xa723c,0xa7240,0xa7244]
        idx=lambda: rec.index(rd(s,0xa726e,4))
        s.input('JOY2_UP',1);prev=idx();samples=[]
        for i in range(n):
            s.cmd('monitor fields 1',timeout=600)
            cur=idx();samples.append(dict(frames=(cur-prev)%3,delta=rd(s,0xa6f00,2),
                race_field=rd(s,0xa5d4c,4),pos=rd(s,0xa5d64,4)));prev=cur
        s.input('JOY2_UP',0);s.shot('5-after.png')
        frames=sum(x['frames'] for x in samples);fields=2*n
        res=dict(setup=os.environ.get('AMIGA_SETUP','a1200-fast'),fields=fields,frames=frames,
                 fps=frames*50/fields,deltas=dict(sorted(collections.Counter(x['delta'] for x in samples).items())),
                 race_fields=samples[-1]['race_field']-samples[0]['race_field'],samples=samples)
        json.dump(res,open(os.path.join(out,'rate.json'),'w'),indent=1)
        print({k:v for k,v in res.items() if k!='samples'})
    finally:s.quit()
