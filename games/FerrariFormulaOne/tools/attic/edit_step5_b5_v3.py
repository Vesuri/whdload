from pathlib import Path
import math
p=Path('Games/FerrariFormulaOne_Sqrt.s');s=p.read_text();a=s.index('FF1SquareRootU32:\n');s=s[:a]+s[a:].replace('FF1SquareRootU32:\n','''FF1SquareRootU32:
        cmpi.l  #1024,d0
        bhs.b   .wide
        ; The same seed table gives exact small roots without division.
        move.w  FF1RootSeeds(pc,d0.w*2),d0
        lsr.l   #8,d0
        lsr.l   #3,d0
        rts
.wide:
''',1)
a=s.index('        move.l  FF1RootSeeds(pc,d1.w*4),d2');b=s.index('        ; Upper bucket root',a)
s=s[:a]+'''        move.l  #65536,d2
        cmpi.w  #1023,d1
        beq.b   .upper
        moveq   #0,d2
        move.w  FF1RootSeeds+2(pc,d1.w*2),d2
.upper:
'''+s[b:]
a=s.index('        move.l  FF1RootSeeds(pc,d2.w*4),d5');b=s.index('        add.l   d1,d5',a)
s=s[:a]+'''        moveq   #0,d5
        move.w  FF1RootSeeds(pc,d2.w*2),d5
        move.l  #65536,d4
        cmpi.w  #1023,d2
        beq.b   .upper
        moveq   #0,d4
        move.w  FF1RootSeeds+2(pc,d2.w*2),d4
.upper:
        sub.l   d5,d4
        moveq   #6,d2
        lsr.l   d2,d1
        andi.l  #$ffff,d1
        mulu.w  d4,d1
        swap    d5
'''+s[b:]
a=s.index('FF1RootSeeds:\n')+len('FF1RootSeeds:\n');b=s.index('        else\n',a)
vals=[f'${math.isqrt(k<<22):04x}' for k in range(1024)]
s=s[:a]+'''; Entry k = isqrt(k << 22), k=0..1023. The endpoint k=1024 is
; exactly 65536 and handled in code. Integer generation avoids rounding.
'''+''.join('        dc.w '+','.join(vals[i:i+8])+'\n' for i in range(0,1024,8))+s[b:];p.write_text(s)
# Avoid temporary output slots once both axis checks have succeeded.
p=Path('Games/FerrariFormulaOne_Velocity.s');s=p.read_text()
for start,end in [('FF1VelocityRotate020:','FF1VelocityShift15:'),('FF1VelocityProject020:','FF1VelocityApply20:')]:
 a=s.index(start);b=s.index(end,a);part=s[a:b]
 part=part.replace('        suba.w  #8,sp','''        ifd FF1_HELPERS_020
        suba.w  #4,sp
        else
        suba.w  #8,sp
        endc''').replace('        move.l  d4,4(sp)\n        move.l  (sp),(a0)\n        move.l  4(sp),4(a0)','''        ifd FF1_HELPERS_020
        move.l  d4,4(a0)
        move.l  (sp),(a0)
        else
        move.l  d4,4(sp)
        move.l  (sp),(a0)
        move.l  4(sp),4(a0)
        endc''').replace('        adda.w  #8,sp','''        ifd FF1_HELPERS_020
        adda.w  #4,sp
        else
        adda.w  #8,sp
        endc''')
 s=s[:a]+part+s[b:]
a=s.index('        ifd FF1_HELPERS_020\n',s.index('FF1VelocityShift15:'));b=s.index('        else\n',a)
s=s[:a]+'''        ifd FF1_HELPERS_020
        ; Double then shift by a word. Check both signed overflow and the
        ; discarded high word before committing either output component.
        add.l   d4,d4
        addx.l  d5,d5
        bvs.b   .overflow
        move.w  d5,d6
        ext.l   d6
        cmp.l   d5,d6
        bne.b   .overflow
        swap    d4
        move.w  d5,d4
        swap    d4
        moveq   #0,d1
        rts
'''+s[b:]
# Existing common tail must belong only to old implementation.
s=s.replace('        endc\n        or.l    d5,d4','        or.l    d5,d4',1).replace('.overflow:\n        moveq   #-1,d1\n        rts\n\n; A0 vector', '        endc\n.overflow:\n        moveq   #-1,d1\n        rts\n\n; A0 vector',1)
# Conversion-only signed division: do not touch native exact-CCR division.
a=s.index('FF1VelocityApply20:\n');b=s.index('; Rotate Q16 velocity AND',a);old=s[a:b]
s=s[:a]+'''        ifd FF1_HELPERS_020
FF1VelocityApply20:
        movem.l d0/d2-d4,-(sp)
        move.l  (a2),d0
        move.w  (a1),d2
        ext.l   d2
        add.l   d2,d0
        bvs.b   .bad
        divsl.l #5,d2:d0
        add.l   (a0),d0
        bvs.b   .bad
        move.l  d0,d4
        move.l  4(a2),d0
        move.w  2(a1),d3
        ext.l   d3
        add.l   d3,d0
        bvs.b   .bad
        divsl.l #5,d3:d0
        add.l   4(a0),d0
        bvs.b   .bad
        move.l  d4,(a0)
        move.l  d0,4(a0)
        move.w  d2,(a1)
        move.w  d3,2(a1)
        moveq   #0,d1
        bra.b   .done
.bad:
        moveq   #-1,d1
.done:
        movem.l (sp)+,d0/d2-d4
        rts
        else
'''+old+'''        endc

'''+s[b:]
p.write_text(s)
# Wear validates before changing D0; its common small unsigned numerator can
# use an exact quotient/remainder table, retaining full-domain division.
p=Path('Games/FerrariFormulaOne_Wear.s');s=p.read_text().replace('        movem.l d2-d4,-(sp)\n        move.l  d0,d4','''        ifd FF1_HELPERS_020
        movem.l d2-d3,-(sp)
        else
        movem.l d2-d4,-(sp)
        move.l  d0,d4
        endc''').replace('        moveq   #0,d2\n        divu.l  #5,d2:d0','''        ifd FF1_HELPERS_020
        cmpi.l  #255,d0
        bhi.b   .divide
        move.w  FF1WearFifths(pc,d0.w*2),d2
        moveq   #0,d0
        move.b  d2,d0
        lsr.w   #8,d2
        bra.b   .clamp
.divide:
        divul.l #5,d2:d0
.clamp:
        else
        moveq   #0,d2
        divu.l  #5,d2:d0
        endc''').replace('        move.l  d4,d0','''        ifnd FF1_HELPERS_020
        move.l  d4,d0
        endc''').replace('        movem.l (sp)+,d2-d4','''        ifd FF1_HELPERS_020
        movem.l (sp)+,d2-d3
        else
        movem.l (sp)+,d2-d4
        endc''')
s+='''        ifd FF1_HELPERS_020
; Packed unsigned remainder:quotient for every numerator 0..255.
FF1WearFifths:
FF1WearNumerator set 0
        rept 256
        dc.w ((FF1WearNumerator%5)<<8)|(FF1WearNumerator/5)
FF1WearNumerator set FF1WearNumerator+1
        endr
        endc
''';p.write_text(s)
r=Path('tmp/dev/tools')
for name in ('build_step5_b5.py','profile_step5_b5.py','capture_step5_b5_matrix.py','analyze_step5_b5_states.py','analyze_step5_b5_elapsed.py','analyze_step5_b5_replay.py','analyze_step5_b5_profiles.py'):
 p=r/name;t=p.read_text().replace('b5-v2','b5-v3').replace("ver='v2'","ver='v3'");p.write_text(t)
