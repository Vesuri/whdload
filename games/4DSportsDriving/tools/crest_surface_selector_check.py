#!/usr/bin/env python3
"""Check native centre-lane surface selection from map data, not SELECT planes.

This deliberately stops short of the barrier/cached-wheel logic: it establishes
which plane the centre-lane path uses. It is not a general collision query.
"""
import hashlib,json,struct
from pathlib import Path
from native_contact_response import word
ROOT=Path(__file__).resolve().parents[1]
cap=ROOT/'tmp/prof/contact-prediction-d9'
meta=json.loads((cap/'anchor.json').read_text())
ram=(cap/'memory.bin').read_bytes()
a4=meta['data_base']+0x7ffe
base=meta['memory_base']
def read(addr,fmt):return struct.unpack_from('>'+fmt,ram,addr-base)[0]
def w(off):return read(a4+off,'h')
def ptr(off):return read(a4+off,'I')
def select(position):
    # Conditional centre-lane model: kind16 also tests PREVIOUS cached X.
    # Before using with altered motion, independently establish that previous
    # cached X is strictly inside +/-120; new X alone does not prove this.
    x,y,z=[word(v>>6) for v in position]
    tx,tz=x>>10,z>>10
    if not (0<=tx<30 and 0<=tz<30):raise ValueError('outside map')
    terrain=read(ptr(-0x1774)+w(-0x1990+2*tz)+tx,'B')
    track=read(ptr(-0x1778)+w(-0x1954+2*tz)+tx,'B')
    if track>=253:raise ValueError('multi-tile lookup unsupported')
    entry=a4-0x5b0c+20*track
    orientation=read(entry+4,'h');kind=read(entry+18,'b')
    if read(entry+17,'B'):raise ValueError('shifted tile origin unsupported')
    bx,bz=w(-0x17ec+2*tx),w(-0x1864+2*tz)
    lx,lz=word(x-bx),word(z-bz)
    if kind==22 and terrain==0 and orientation==768 and abs(lx)<120 and y<=390:
        # $1292A..$12950 lower crossing road: rotated local Z=-world local X.
        # Upper-deck and side/barrier cases remain unsupported.
        return dict(plane=0,base_x=bx,base_y=2,base_z=bz,
                    track=track,terrain=terrain,kind=kind,orientation=orientation)
    if orientation==512:lx,lz=word(-lx),word(-lz)
    elif orientation!=0:raise ValueError('rotated lane unsupported')
    if abs(lx)>=120:raise ValueError('outside strict centre lane')
    if kind==0 and terrain==0 and orientation==0 and lz>=-300:
        # $123C8..$12400: after the start gantry's -300 Z boundary the
        # strict centre lane is ordinary road on plane0. Earlier cells excluded.
        plane=0
    elif kind==1 and terrain in (0,6):plane=0
    elif (kind,terrain)==(1,7):plane=12
    elif (kind,terrain)==(16,0):plane=12+(2 if orientation==512 else 0)
    else:raise ValueError('unsupported terrain/track combination')
    # $13D9E..$13DBC: non-grass centre lane is raised by two coarse units.
    # Terrain6 dispatch at $12008 selects $11F66: height from a4-$771A.
    base_y=word(w(-0x771a)+2) if terrain==6 else 2
    return dict(plane=plane,base_x=bx,base_y=base_y,base_z=bz,
                track=track,terrain=terrain,kind=kind,orientation=orientation)

def main():
    records=json.loads((cap/'prediction.json').read_text())['records']
    groups={};failures=[];queries=0
    # ENTRY translated wheel coordinates are independent of SELECT output.
    for entry in records['ENTRY']:
        tick=entry[0]
        for wheel in range(4):
            v=entry[57+3*wheel:60+3*wheel]
            got=select(v);expected=records['SELECT'][queries]
            assert (expected['tick'],expected['wheel'])==(tick,wheel)
            bad={k:[got[k],expected[k]] for k in ('plane','base_x','base_y','base_z') if got[k]!=expected[k]}
            if bad:failures.append(dict(tick=tick,wheel=wheel,fields=bad))
            key=str((got['track'],got['terrain'],got['plane']))
            groups[key]=groups.get(key,0)+1;queries+=1
    report=dict(queries=queries,groups=groups,failures=failures,
        snapshot_sha256=hashlib.sha256(ram).hexdigest(),
        scope='Independent native map/centre-lane plane and base-origin selection from ENTRY positions. Does not model cached-wheel barrier crossing, surface flags, node data, clearance, or arbitrary tracks. No changed-motion live validation yet.')
    (ROOT/'tmp/prof/crest-surface-selector-check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));assert not failures
if __name__=='__main__':main()
