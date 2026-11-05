#!/usr/bin/env python3
import os,shutil,subprocess,json,itertools
from pathlib import Path
from harness import ROOT,sha
out=ROOT/'tmp/handling-collision/units';out.mkdir();stage=out/'source';shutil.copytree(ROOT/'src',stage)
trunc=lambda x,d:(-1 if x<0 else 1)*(abs(x)//d)
values=sorted({0,*[sign*x for sign in [-1,1] for x in [1,26214,26215,32767,65535,65536,65537,113020,169530,655360,32*65536]]})
cv=[]
for period,x in itertools.product([2,5],values):
 for carry in (range(-4,5) if period==2 else [0]):
  whole=(trunc(x*5,period)//65536)*65536;n=whole*period+carry;z=trunc(n,5);cv.append([period,x,carry,z,n-z*5])
tv=[]
for scale,width,centre in itertools.product([0x9160,0x2d6e],range(320,1281,64),[-32768,-257,-1,0,160,32767]):
 product=scale*width;result=((product&65535)<<16)|(((product>>16)+centre)&65535);tv.append([scale,width,centre,result if result<2**31 else result-2**32])
p=stage/'simulation-verify.s';s=p.read_text().replace('    bsr verify_units\n','    bsr verify_units\n    bsr handling_units\n',1)
s+='''
handling_units:
    movem.l d0-a6,-(sp)
    move.w sim_p(pc),-(sp)
    move.w sim_curve_carry(pc),-(sp)
    lea handling_unit_data(pc),a4
    adda.l #29306,a4
    lea handling_curve_vectors(pc),a2
    move.w #CURVE_COUNT-1,d7
.curve
    lea sim_p(pc),a0
    move.l (a2)+,d0
    move.w d0,(a0)
    move.l (a2)+,d4
    move.l d4,-26196(a4)
    lea sim_curve_carry(pc),a0
    move.l (a2)+,d0
    move.w d0,(a0)
    move.l a0,d3
    move.l #$12345678,d1
    bsr sim_curve_step
    move.l d0,d5
    move.l d1,d0
    move.l #$12345678,d1
    bsr verify_equal
    move.l d5,d0
    move.l (a2)+,d1
    bsr verify_equal
    move.w sim_curve_carry(pc),d0
    ext.l d0
    move.l (a2)+,d1
    bsr verify_equal
    move.l -26196(a4),d0
    move.l d4,d1
    bsr verify_equal
    move.l a0,d0
    move.l d3,d1
    bsr verify_equal
    dbf d7,.curve
    lea handling_traffic_vectors(pc),a2
    move.w #TRAFFIC_COUNT-1,d7
.traffic
    move.l (a2)+,d2
    or.l #$abcd0000,d2
    move.l (a2)+,d0
    move.w d0,-29296(a4)
    move.l (a2)+,d0
    move.w d0,-29306(a4)
    move.l #$12345678,d0
    move.l #$76543210,d1
    bsr traffic_near_edge
    move.l d1,d3
    move.l #$12345678,d1
    bsr verify_equal
    move.l d3,d0
    move.l #$76543210,d1
    bsr verify_equal
    move.l d2,d0
    move.l (a2)+,d1
    bsr verify_equal
    dbf d7,.traffic
    lea sim_curve_carry(pc),a0
    move.w (sp)+,(a0)
    lea sim_p(pc),a0
    move.w (sp)+,(a0)
    movem.l (sp)+,d0-a6
    rts
handling_curve_vectors:
'''.replace('CURVE_COUNT',str(len(cv))).replace('TRAFFIC_COUNT',str(len(tv)))
s+=''.join('    dc.l '+','.join(map(str,x))+'\n' for x in cv)+'handling_traffic_vectors:\n'+''.join('    dc.l '+','.join(map(str,x))+'\n' for x in tv)+'handling_unit_data: dcb.b 3114,0\n    even\n';p.write_text(s)
args=[os.environ['VASM'],'-DVERIFY=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+os.environ['AMIGA_INCLUDE'],'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['AMIGA_SHARE']+'/ndk/Include_I','-L',str(out/'slave.slave.lst'),'-o',str(out/'slave.slave'),'TestDriveHD.s'];subprocess.run(args,cwd=stage,check=True)
(out/'vectors.json').write_text(json.dumps(dict(curve=cv,traffic=tv,assertions=len(cv)*5+len(tv)*3,expected_count=668+len(cv)*5+len(tv)*3,source={f.name:sha(f) for f in (ROOT/'src').iterdir() if f.is_file()}),indent=2)+'\n')
