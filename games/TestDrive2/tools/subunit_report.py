#!/usr/bin/env python3
"""Compare completed sub-unit road captures; report quantisation and bounds honestly.
  subunit_report.py OFF/render ON/render [ZERO/render BASELINE_DEMO/render]
Road-row indices change meaning at whole-unit crossings. Match world segments,
not a fixed row index, when measuring boundary continuity.
"""
import argparse,csv,json,re,struct
from pathlib import Path

def records(path,view='main'):
    result=[]
    for f in sorted(path.glob(f'{view}-*.bin')):
        b=f.read_bytes();a=0x7ffe
        w=lambda off:struct.unpack_from('>h',b,a+off)[0]
        u=lambda off:struct.unpack_from('>I',b,a+off)[0]
        rows=[struct.unpack_from('>26h',b,a-5702+52*k) for k in range(44 if view=='main' else 24)]
        phase=lambda y:w(-7606)+(1 if view=='main' else -1)*w(-7574+16*y+12)
        band=[y for y in range(max(1,w(-14944)+1),rows[0][6])
              if (phase(y)^phase(y-1))&8]
        result.append(dict(file=f.name,data=b,rows=rows,camera=u(-13394),heading=w(-13388),lane=u(-13382),band=band))
    return result

def summary(path):
    rr=records(path); changed=moved=0;jumps=[];labels=[];bounds=[]
    for r in rr:
        yy=[row[6] for row in r['rows']]
        if max(yy)>yy[0] or yy[0]>117:bounds.append((r['file'],yy[0],max(yy)))
    for prev,r in zip(rr,rr[1:]):
        if prev['camera']==r['camera']:continue
        changed+=1
        # The edge and colour-band changes are visible motion even if y rounds alike.
        geom=lambda q:[row[:7] for row in q['rows']]
        if geom(prev)!=geom(r) or prev['band']!=r['band']:moved+=1
        labels.append(abs(r['rows'][1][6]-prev['rows'][1][6]))
        shift=(r['camera']>>16)-(prev['camera']>>16)
        for k in range(1,len(r['rows'])):
            old=k+shift
            if 0<=old<len(prev['rows']):jumps.append(abs(r['rows'][k][6]-prev['rows'][old][6]))
    print(path, f'{len(rr)} frames; geometry/colour motion {moved}/{changed} changed-distance frames; row-1 max jump {max(labels,default=0)} px; matched-boundary max {max(jumps,default=0)} px; overruns {len(bounds)}')
    if bounds:raise AssertionError(bounds[:8])
    for view in ('mirror',):
        for r in records(path,view):
            yy=[row[6] for row in r['rows']]
            assert max(yy)<=yy[0]<=117,(view,r['file'],yy)
    output=path/'road-motion.csv'
    with output.open('w',newline='') as f:
        out=csv.writer(f);out.writerow(['frame','camera_16_16','row1_y','nearest_colour_boundary_y','all_boundaries_y'])
        for r in rr:out.writerow([r['file'],r['camera'],r['rows'][1][6],max(r['band'],default=''),';'.join(map(str,r['band']))])
    print('per-frame road values:',output)
    return rr

def zero_scales(path):
    checks=0
    for view in ('main','mirror'):
        for r in records(path,view):
            b=r['data'];a=0x7ffe
            word=lambda off:struct.unpack_from('>H',b,a+off)[0]
            fields,tables,count=( (18,22,26,48),(-26780,-26870,-26690),44 ) if view=='main' else ((20,24,28,50),(-26968,-27018,-26918),24)
            for k in range(count):
                expected=[word(t+2*k) for t in tables]
                expected.append((expected[-1]*162)&65535)
                actual=[word(-5702+52*k+f) for f in fields]
                assert actual==expected,(r['file'],k,actual,expected)
                checks+=4
    print('zero source scales:',checks,'exact words')

def identity(zero,base,initialised=False):
    for view in ('main','mirror'):
        lookup={}
        key=lambda r:(r['camera']>>16,r['heading'],r['lane']>>16)
        for r in records(base,view):lookup.setdefault(key(r),[]).append(r)
        count=0;errors=[];stale=[]
        for r in records(zero,view):
            candidates=lookup.get(key(r),[])
            if not candidates:continue
            a=0x7ffe;data=r['data']
            word=lambda off:struct.unpack_from('>h',data,a+off)[0]
            # The shared table retains unused lines from earlier views/frames.
            # Compare full row records and all lines the current pass writes.
            low=word(-14944);high=r['rows'][0][6]
            if initialised:low,high=0,117
            columns=list(range(16)) if initialised else list(range(8))+list(range(12,16))
            if not initialised and word(-3152):columns+=list(range(8,10))
            blocks=lambda q:(q['data'][a-5702:a-5702+44*52],bytes(q['data'][a-7574+16*y+x] for y in range(low,high) for x in columns))
            matches=[c for c in candidates if blocks(r)==blocks(c)]
            if not matches:errors.append(r['file'])
            elif not any(data[a-7574:a-7574+118*16]==c['data'][a-7574:a-7574+118*16] for c in matches):stale.append(r['file'])
            count+=1
        print('zero identity',view,f'{count} matched-input frames; {len(errors)} row/drawn-line mismatches; {len(stale)} retain different unused-field history',errors[:8])
        assert count and not errors

def cars(path):
    observations=[]
    for line in (path/'gdb.txt').read_text().splitlines():
        if not line.startswith('TD2CAR '):continue
        parts=line.split();kind=parts[1];values=list(map(int,parts[2:]))
        if len(values)<9:continue
        field,view,segment,x,y,row,camera,frac,source=values
        gap=((segment<<16)+frac-camera)/65536
        observations.append((kind,source,field,view,gap,x,y,camera))
    with (path/'car-motion.csv').open('w',newline='') as f:
        out=csv.writer(f);out.writerow(['kind','source','field','view','gap_units','x','y','camera_16_16']);out.writerows(observations)
    for kind in ('opponent','forward','oncoming','police'):
        found=[r for r in observations if r[0]==kind and r[3]==0]
        episodes=[]
        for i,r in enumerate(found):
            group=[q for q in found[i:] if q[1]==r[1] and 0<=q[2]-r[2]<=100]
            for length in range(4,len(group)+1):
                chunk=group[:length]
                gapspan=max(q[4] for q in chunk)-min(q[4] for q in chunk)
                ticks=(max(q[7] for q in chunk)>>16)-(min(q[7] for q in chunk)>>16)
                if gapspan<=0.5 and ticks>=2:
                    episodes.append((length,gapspan,max(q[6] for q in chunk)-min(q[6] for q in chunk),chunk[0][2],chunk[-1][2],ticks))
        best=max(episodes,default=None)
        print(path,kind,f'{len(found)} main-view draws; longest <=0.5-unit-gap episode (frames, gap span, y span, fields, camera ticks):',best)

def check_car_coordinates(path,subunit):
    """Compare captured draw registers with geometry and latched positions."""
    meta=json.loads((path/'metadata.json').read_text())
    assets=(path/'assets.bin').read_bytes();base=meta['assets_base']
    current={};counts={};partial=0
    wrap=lambda n:(n+32768)%65536-32768
    for line in (path/'gdb.txt').read_text().splitlines():
        if line.startswith('TD2ROW '):
            _,view,index,_=line.split()
            current[0 if view=='main' else 2]=(path/f'{view}-{int(index):04d}.bin').read_bytes()
        if not line.startswith('TD2CAR '):continue
        _,kind,*numbers=line.split()
        field,view,segment,x,y,k,camera,fraction,source=map(int,numbers)
        if view not in current:
            partial+=1           # capture can start during an already drawn view
            continue
        b=current[view];a=0x7ffe
        word=lambda off:struct.unpack_from('>h',b,a+off)[0]
        def xy(row):
            offset=-5702+52*row
            centre,height=word(offset+10),word(offset+12)
            if kind in ('opponent','police'):
                lateral=word(-13370 if kind=='opponent' else -13362)
                scale=word(offset+48+view)&65535
                return wrap(centre+(lateral*scale>>16)),height
            typ=struct.unpack_from('>h',assets,source-base-2)[0]
            half=(word(offset+26+view)&65535)>>1
            if kind=='forward':xx=centre+half if typ==25 else word(offset+4)-half
            else:xx=centre-half if typ==17 else word(offset+2)+half
            return wrap(xx),height
        expected=xy(k)
        if subunit:
            if k==0:
                camera_fraction=camera&65535
                weight=((camera_fraction-fraction) if view else (fraction-camera_fraction))>>1
                neighbour=1
            else:
                weight=fraction>>1
                neighbour=k-1 if view else k+1
                if not view and k==43:weight=0
            if weight:
                other=xy(neighbour)
                expected=tuple(wrap(v+(wrap(z-v)*weight>>15)) for v,z in zip(expected,other))
        assert expected==(x,y),(path,kind,field,k,expected,(x,y))
        counts[kind]=counts.get(kind,0)+1
    print(path,'exact car x/y against completed road rows:',counts,'; initial draws without a completed-row capture:',partial)
    assert counts.get('opponent',0) and counts.get('forward',0) and counts.get('oncoming',0),'capture must cover opponent and both traffic directions'


def constant_gap(path):
    """Held flat-road inputs isolate camera/car fraction cancellation.

    check_car_coordinates first validates this integer projection arithmetic
    against live draw registers. This sweep is a geometric fixture, not a
    claim that the demo holds a particular gap or that sprite LOD is continuous.
    """
    b=next(path.glob('main-*.bin')).read_bytes();a=0x7ffe
    word=lambda off:struct.unpack_from('>h',b,a+off)[0]
    for mirror in (False,True):
        table=-26968 if mirror else -26780
        offset=29 if mirror else 76
        for k in (1,5,10):
            alone=[];cars=[]
            for fraction in range(0,65536,256):
                q=fraction>>1
                def y(row):
                    scale=word(table+2*row)
                    if row:
                        other=row+1 if mirror else row-1
                        scale+=(word(table+2*other)-scale)*q>>15
                    return offset+(83*scale>>16)
                matched=y(k);next_y=y(k-1 if mirror else k+1)
                alone.append(matched);cars.append(matched+((next_y-matched)*q>>15))
            span=max(cars)-min(cars)
            print('constant-gap flat fixture',('mirror' if mirror else 'main'),f'row {k}: road-only span {max(alone)-min(alone)} px; road+car {span} px; whole-unit reset {abs(cars[-1]-cars[0])} px')
            assert span<=(2 if mirror and k==1 else 1) and abs(cars[-1]-cars[0])<=1,'a constant-gap car retains a whole-unit sawtooth'


def fractional_gap(path):
    """Sweep sub-unit car/camera carries at fixed noninteger interior gaps."""
    b=next(path.glob('main-*.bin')).read_bytes();a=0x7ffe
    word=lambda off:struct.unpack_from('>h',b,a+off)[0]
    for mirror in (False,True):
        table=-26968 if mirror else -26780
        offset=29 if mirror else 76
        for nominal in ((5,10) if mirror else (1,5,10)):
            for gap_fraction in (16384,32768,49152):
                values=[]
                for camera in range(0,65536,256):
                    carry,car=divmod(camera+gap_fraction,65536)
                    row=nominal-carry if mirror else nominal+carry
                    def y(k):
                        scale=word(table+2*k)
                        neighbour=k+1 if mirror else k-1
                        if k:scale+=(word(table+2*neighbour)-scale)*(camera>>1)>>15
                        return offset+(83*scale>>16)
                    matched=y(row);neighbour=y(row-1 if mirror else row+1)
                    values.append(matched+((neighbour-matched)*(car>>1)>>15))
                jumps=[abs(right-left) for left,right in zip(values,values[1:])]
                jumps.append(abs(values[-1]-values[0]))
                print('fractional-gap flat fixture',('mirror' if mirror else 'main'),nominal,gap_fraction,'largest carry/per-sample y jump',max(jumps),'px')
                assert max(jumps)<=1,'a fractional-gap car jumps at a car/camera unit carry'


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('off',type=Path);p.add_argument('on',type=Path)
    p.add_argument('zero',type=Path,nargs='?');p.add_argument('baseline',type=Path,nargs='?')
    p.add_argument('--check-cars',action='store_true',help='verify actual car x/y and sweep a constant-gap flat-road fixture')
    p.add_argument('--initialised',action='store_true',help='both zero-identity arms initialise the entire scanline buffer')
    a=p.parse_args();summary(a.off);summary(a.on);cars(a.off);cars(a.on)
    if a.check_cars:
        check_car_coordinates(a.off,False);check_car_coordinates(a.on,True);constant_gap(a.on);fractional_gap(a.on)
    if a.zero:zero_scales(a.zero)
    if a.zero and a.baseline:identity(a.zero,a.baseline,a.initialised)
