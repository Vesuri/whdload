#!/usr/bin/env python3
"""Guest vectors for production steering pose helpers, using private scratch data."""
import os,shutil,subprocess,json,itertools
from pathlib import Path
from harness import ROOT,sha
out=ROOT/'tmp/steer-reversal/units';out.mkdir();stage=out/'source';shutil.copytree(ROOT/'src',stage)
v=[]
for p,e,w,c in itertools.product([2,5],[-393216,-157287,0,157287,393216],[-655360,-1,0,1,655360],[-65536,0,65536]):
 pose=c-((e+w)//4);z=pose+e//4;coarse=(-1 if z<0 else 1)*(abs(z)*5//p);v.append([p,e,w,pose,coarse//16])
p=stage/'simulation-verify.s';s=p.read_text().replace('    bsr verify_units\n','    bsr verify_units\n    bsr steer_units\n',1)
s+='''
steer_units:
    movem.l d0-a6,-(sp)
    move.w sim_p(pc),-(sp)
    move.l sim_visual_edge(pc),-(sp)
    lea steer_unit_data(pc),a4
    adda.l #26204,a4
    lea steer_unit_vectors(pc),a2
    move.w #149,d7
.next
    lea sim_p(pc),a0
    move.l (a2)+,d0
    move.w d0,(a0)
    move.l (a2)+,d4
    move.l d4,-26200(a4)
    move.l (a2)+,d5
    move.l d5,-22356(a4)
    move.l (a2)+,d6
    move.l d6,-26204(a4)
    bsr sim_visual_edge_capture
    move.l d5,d1
    asr.l #8,d1
    bsr verify_equal
    move.l sim_visual_edge(pc),d0
    move.l d4,d1
    bsr verify_equal
    move.l #$12345678,d1
    bsr sim_bank_pose
    move.l d0,d3
    move.l d1,d0
    move.l #$12345678,d1
    bsr verify_equal
    move.l d3,d0
    move.l (a2)+,d1
    bsr verify_equal
    move.l -26200(a4),d0
    move.l d4,d1
    bsr verify_equal
    move.l -26204(a4),d0
    move.l d6,d1
    bsr verify_equal
    move.l -22356(a4),d0
    move.l d5,d1
    bsr verify_equal
    dbf d7,.next
    lea sim_visual_edge(pc),a0
    move.l (sp)+,(a0)
    lea sim_p(pc),a0
    move.w (sp)+,(a0)
    movem.l (sp)+,d0-a6
    rts
steer_unit_vectors:
'''+''.join('    dc.l '+','.join(map(str,x))+'\n' for x in v)+'''steer_unit_data: dcb.b 3852,0
    even
'''
p.write_text(s)
args=[os.environ['VASM'],'-DVERIFY=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym','-I'+os.environ['AMIGA_INCLUDE'],'-I'+os.environ['WHDLOAD']+'/Include','-I'+os.environ['WHDLOAD']+'/Src/sources','-I'+os.environ['AMIGA_SHARE']+'/ndk/Include_I','-L',str(out/'slave.slave.lst'),'-o',str(out/'slave.slave'),'TestDriveHD.s']
subprocess.run(args,cwd=stage,check=True)
(out/'vectors.json').write_text(json.dumps(dict(vectors=v,assertions=150*7,source={p.name:sha(p) for p in (ROOT/'src').iterdir() if p.is_file()}),indent=2)+'\n')
