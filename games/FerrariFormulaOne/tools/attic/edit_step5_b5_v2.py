from pathlib import Path
p=Path('Games/FerrariFormulaOne_Sqrt.s');s=p.read_text();a=s.index('FF1SquareRootU32:\n');b=s.index('FF1SquareRootU64:\n',a)
s=s[:a]+'''FF1SquareRootU32:
        movem.l d1-d4,-(sp)
        move.l  d0,d4
        beq.b   .done
        bfffo   d0{0:32},d3
        andi.l  #30,d3
        lsl.l   d3,d0
        move.l  d0,d1
        moveq   #22,d2
        lsr.l   d2,d1
        move.l  FF1RootSeeds(pc,d1.w*4),d2
        moveq   #0,d0
        move.w  d2,d0
        swap    d2
        andi.l  #$ffff,d2
        add.l   d0,d2
        ; Upper bucket root is within 65 units in the normalized U32 domain.
        lsr.l   #1,d3
        beq.b   .divide
        lsr.l   d3,d2
        addq.l  #1,d2
.divide:
        move.l  d4,d0
        divu.l  d2,d0
        add.l   d2,d0
        lsr.l   #1,d0
        move.l  d0,d2
.correct:
        mulu.w  d0,d0
        cmp.l   d4,d0
        bls.b   .answer
        subq.l  #1,d2
        move.l  d2,d0
        bra.b   .correct
.answer:
        move.l  d2,d0
.done:
        movem.l (sp)+,d1-d4
        rts
''' + s[b:]
a=s.index('        moveq   #0,d3\n',s.index('FF1SquareRootU64:\n'));b=s.index('.seed:\n',a)
s=s[:a]+'''        moveq   #0,d3
        tst.l   d1
        bne.b   .high
        move.l  d0,d1
        moveq   #0,d0
        moveq   #16,d3
.high:
        bfffo   d1{0:32},d4
        andi.l  #30,d4
        beq.b   .seed
        moveq   #32,d5
        sub.l   d4,d5
        move.l  d0,d2
        lsr.l   d5,d2
        lsl.l   d4,d1
        or.l    d2,d1
        ; Only normalized bits 63..38 are needed for seed interpolation.
        lsr.l   #1,d4
        add.l   d4,d3
''' + s[b:]
p.write_text(s)
r=Path('tmp/dev/tools')
for name in ('build_step5_b5.py','profile_step5_b5.py','capture_step5_b5_matrix.py','analyze_step5_b5_states.py','analyze_step5_b5_elapsed.py','analyze_step5_b5_replay.py','analyze_step5_b5_profiles.py'):
 p=r/name;t=p.read_text().replace('b5-v1','b5-v2').replace("ver='v1'","ver='v2'");p.write_text(t)
