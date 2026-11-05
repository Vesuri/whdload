#!/usr/bin/env python3
"""Native bitmap replay against independently tiled backgrounds; no timing claims."""
import argparse, hashlib, json, re, struct
from pathlib import Path
from ocs_display_check import Native, CODE, STACK, long
from ocs_reconstruct import ROOT, new_output


def check(variant, build, capture, model):
    layout=json.loads((capture/'layout.json').read_text())
    report=json.loads((capture/'report.json').read_text())
    name='WingCommander.Slave' if variant=='ocs' else 'WingCommanderCD32.Slave'
    assert report['complete'] and report['variant']==variant
    assert report['slave_sha256']==hashlib.sha256((build/name).read_bytes()).hexdigest()
    sy=(json.loads((build/'build.json').read_text())['symbols'] if variant=='ocs' else
        {n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(build/'slave.lst').read_text(),re.M)})
    c=Native(ROOT/'tmp/originals/ocs/WingCommander/data/Wing.english',model=model)
    try:
        c.write(0,(capture/'chip.bin').read_bytes());c.write(0x200000,(capture/'fast.bin').read_bytes())
        h0,h1,_,_=layout['hunks'];a4=h1+0x7ffe;entry=layout['slave']+sy['cinematic_background']
        sp=int(re.search(r'^sp\s+0x([0-9a-f]+)',(capture/'registers.txt').read_text(),re.M)[1],16)
        surface,x,y,asset,frame=struct.unpack('>IhhIH',c.read(sp,14))
        assert x==0 and y==0 and frame==0
        x0,y0,x1,y1=struct.unpack('>hhhh',c.read(surface+24,8))
        assert (x0,y0,x1,y1)==(0,0,319,127),(x0,y0,x1,y1)
        rows=[c.get(c.get(surface,4)+4*y,4) for y in range(128)]
        original=h0+(0x2f9a6 if variant=='ocs' else 0x2efe8)
        sites=(0x1d0f2,0x1d10e,0x1d222,0x1d23e) if variant=='ocs' else (0x1de20,0x1de3c,0x1df50,0x1df6c)
        for site in sites:assert c.read(h0+site,6)==bytes.fromhex('4eb9')+long(entry)
        def fill(value):
            for row in rows:c.write(row,bytes([value])*320)
        def pixels():return b''.join(c.read(row,320) for row in rows)
        regs={r:0x123400+r for r in (*range(3,8),*range(11,17))};regs[5]=a4
        def draw(target,x,frame):
            args=struct.pack('>IhhIH',surface,x,0,asset,frame)
            c.run(target-CODE,args,regs)
            for r,v in regs.items():assert c.reg(r)==v,('callee register',r)
            assert c.reg(8)==STACK+4
        tiles=[]
        for frame in range(3):
            fill(0x55);draw(original,0,frame);image=pixels()
            fill(0xaa);draw(original,0,frame)
            assert pixels()==image,('tile is not opaque',frame)
            tiles.append(image)
        assert tiles[0]!=tiles[1], 'alternating-background control lacks distinct tiles'
        cases=0;negative=0
        # Native scenes start at zero and advance by 12: pixel pairs stay even.
        # Beyond two complete tile periods, plus even edge/word boundaries.
        for phase in sorted(set(range(0,-1300,-12))|{-318,-320,-322,-638,-640,-642,0,2,318,320,322}):
            for frames in ((0,1),(2,2)):
                expected=bytearray()
                for y in range(128):
                    strip=tiles[frames[0]][y*320:(y+1)*320]+tiles[frames[1]][y*320:(y+1)*320]
                    expected.extend(strip[(x-phase)%640] for x in range(320))
                # Poison removes any accidental dependence on the previous picture.
                fill(0xa5);draw(entry,phase,frames[0]);draw(entry,phase+320,frames[1])
                assert pixels()==expected,(variant,model,phase,frames)
                cases+=1
                if phase==-360:
                    fill(0xa5);draw(original,phase,frames[0]);draw(original,phase+320,frames[1])
                    assert pixels()!=expected,'missing-wrap negative control did not fail'
                    negative+=1
        return dict(model=model,pixel_cases=cases,missing_wrap_rejected=negative,tiles_opaque=True,alternating_tiles_distinct=True)
    finally:c.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path);p.add_argument('capture',type=Path)
    p.add_argument('--output',required=True);a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    models=(1,2,4) if a.variant=='ocs' else (2,4)
    results=[check(a.variant,a.build,a.capture,m) for m in models]
    (out/'report.json').write_text(json.dumps(dict(complete=True,variant=a.variant,results=results),indent=2)+'\n')
    print('PASS:',results)

if __name__=='__main__':main()
