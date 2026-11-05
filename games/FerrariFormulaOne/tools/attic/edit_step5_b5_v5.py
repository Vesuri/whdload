from pathlib import Path
p=Path('Games/FerrariFormulaOne_Speed.s');s=p.read_text();a=s.index('FF1SpeedRate20:');b=s.index('; Derive scalar speed',a);part=s[a:b];old=part
# Separate conditional implementation avoids assembling mixed register aliases.
part=part.replace('d2-d5','d2-d4').replace('d5','d1')
part=part.replace('        tst.l   d4\n        bmi.b   .bad\n','')
part=part.replace('        move.l  d1,d3\n        moveq   #31,d1\n        asr.l   d1,d3','        move.l  d1,d3\n        swap    d3\n        ext.l   d3')
# Strip conditional since this entire variant is selected only by the same flag.
a1=part.index('        ifd FF1_HELPERS_020\n');b1=part.index('        else\n',a1);c1=part.index('        endc\n',b1)
part=part[:a1]+part[a1+len('        ifd FF1_HELPERS_020\n'):b1]+part[c1+len('        endc\n'):]
part=part.replace('        divs.l  #5,d2:d0','''        ; Use a 32-bit dividend only if its high half is a sign extension.
        move.l  d0,d3
        moveq   #31,d1
        asr.l   d1,d3
        cmp.l   d2,d3
        bne.b   .wide
        divsl.l #5,d2:d0
        bra.b   .divided
.wide:
        divs.l  #5,d2:d0
.divided:''')
# Longer entry needs word branches to the shared rejection path.
part=part.replace('bhi.b   .bad','bhi.w   .bad').replace('blt.b   .bad','blt.w   .bad').replace('bgt.b   .bad','bgt.w   .bad').replace('bvs.b   .bad','bvs.w   .bad')
# Default original body already contains an off-path conditional, harmless but
# remove it for clarity while preserving assembled bytes.
a1=old.index('        ifd FF1_HELPERS_020\n');b1=old.index('        else\n',a1);c1=old.index('        endc\n',b1);old=old[:a1]+old[b1+len('        else\n'):c1]+old[c1+len('        endc\n'):]
s=s[:a]+'        ifd FF1_HELPERS_020\n'+part+'        else\n'+old+'        endc\n\n'+s[b:]
a=s.index('FF1SpeedFromVelocity020:');part=s[a:].replace('        movem.l d0/d2-d7,-(sp)','''        ifd FF1_HELPERS_020
        movem.l d0/d3-d5,-(sp)
        else
        movem.l d0/d2-d7,-(sp)
        endc''').replace('        movem.l (sp)+,d0/d2-d7','''        ifd FF1_HELPERS_020
        movem.l (sp)+,d0/d3-d5
        else
        movem.l (sp)+,d0/d2-d7
        endc''');s=s[:a]+part;p.write_text(s)
p=Path('Games/FerrariFormulaOne_Velocity.s');s=p.read_text()
for label,end,old,new in [('FF1VelocityDerivative20:','; A0 vector','d0/d2-d4','d0/d2-d3'),('FF1VelocityRotate020:','; D5:D4','d0/d2-d7','d2-d7'),('FF1VelocityProject020:','; Integrate a continuous','d0/d2-d7','d2-d6'),('FF1VelocityRotateCarry020:','; Signed D5:D4','d0/d2-d7','d2-d7'),('FF1VelocityLimit020:',None,'d2-d3','d3')]:
 a=s.index(label);b=s.index(end,a) if end else len(s);part=s[a:b]
 part=part.replace(f'        movem.l {old},-(sp)',f'        ifd FF1_HELPERS_020\n        movem.l {new},-(sp)\n        else\n        movem.l {old},-(sp)\n        endc').replace(f'        movem.l (sp)+,{old}',f'        ifd FF1_HELPERS_020\n        movem.l (sp)+,{new}\n        else\n        movem.l (sp)+,{old}\n        endc')
 s=s[:a]+part+s[b:]
p.write_text(s)
p=Path('Games/FerrariFormulaOne_Wear.s');s=p.read_text();# Generate specialized compact-register body alongside unchanged default.
a=s.index('FF1Wear20Delta:');b=s.index('        ifd FF1_HELPERS_020\n; Packed',a)
body='''FF1Wear20Delta:
        move.l  d2,-(sp)
        tst.l   d0
        bmi.b   .bad
        move.l  (a0),d2
        bmi.b   .bad
        moveq   #0,d1
        ifd FF1_PLAYER_HOOKS
        move.b  (a1),d1
        else
        move.w  (a1),d1
        endc
        cmpi.w  #4,d1
        bhi.b   .bad
        add.l   d1,d0
        cmpi.l  #255,d0
        bhi.b   .divide
        move.w  FF1WearFifths(pc,d0.w*2),d1
        moveq   #0,d0
        move.b  d1,d0
        lsr.w   #8,d1
        bra.b   .clamp
.divide:
        divul.l #5,d1:d0
.clamp:
        cmp.l   d2,d0
        blo.b   .store
        move.l  d2,d0
        moveq   #0,d1
.store:
        ifd FF1_PLAYER_HOOKS
        move.b  d1,(a1)
        else
        move.w  d1,(a1)
        endc
        moveq   #0,d1
        bra.b   .done
.bad:
        moveq   #-1,d1
.done:
        move.l  (sp)+,d2
        rts
'''
import subprocess
original=subprocess.check_output(['git','show','HEAD:Games/FerrariFormulaOne_Wear.s']).decode();original=original[original.index('FF1Wear20Delta:'):]
s=s[:a]+'        ifd FF1_HELPERS_020\n'+body+'        else\n'+original+'        endc\n'+s[b:];p.write_text(s)
r=Path('tmp/dev/tools')
for p in r.glob('*step5_b5v4_*.py'):(r/p.name.replace('b5v4','b5v5')).write_text(p.read_text().replace('b5v4','b5v5'))
for name in ('build_step5_b5.py','profile_step5_b5.py','capture_step5_b5_matrix.py','analyze_step5_b5_states.py','analyze_step5_b5_elapsed.py','analyze_step5_b5_replay.py','analyze_step5_b5_profiles.py'):
 p=r/name;p.write_text(p.read_text().replace('b5-v4','b5-v5').replace("ver='v4'","ver='v5'"))
