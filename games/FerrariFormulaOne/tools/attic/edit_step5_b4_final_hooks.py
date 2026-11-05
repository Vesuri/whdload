from pathlib import Path
import re
p=Path('Games/FerrariFormulaOne_UpdateHooks.s');s=p.read_text()
# Two straight-line load/store callbacks. VERIFY keeps the component callbacks
# and their independent records; lean emits their functional state work once.
for name,body in [('heading_67280',''' lea velocity_initialized(pc),a0
 bset #0,(a0)
 bne.b .loaded
 lea velocity_shadow(pc),a0
 move.w $32f94,d0
 move.w $32f96,d1
 bsr.w FF1VelocityReset
 clr.l 8(a0)
.loaded:
 lea fine_cross_pending(pc),a0
 clr.w (a0)
 lea fine_car_crosses(pc),a0
 clr.w (a0)
 lea position_shadow(pc),a0
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 lea speed_shadow(pc),a0
 lea speed_work(pc),a1
 move.l (a0),(a1)
 move.w 4(a0),4(a1)
'''),('heading_6860e',''' lea position_shadow(pc),a0
 move.w $32fc2,(a0)
 move.w $32fc4,6(a0)
 lea speed_work(pc),a0
 lea speed_shadow(pc),a1
 move.l (a0),(a1)
 move.w 4(a0),4(a1)
''')]:
 m=re.search(r'(?m)^'+name+r':\n(.*?)(?=^[A-Za-z_]\w*:)',s,re.S);old=m[1];guard,rest=old.split(' ENDC\n',1);opcode=rest.split('\n')[0];assert opcode.startswith(' dc.w')
 cont='$67286' if name.endswith('67280') else '$68614'
 new=guard+' ENDC\n IFD FF1_LEAN_PLAYER\n'+opcode+'''
 movem.l d0-d1/a0-a1,-(sp)
 move.w ccr,-(sp)
'''+body+''' lea heading_shadow(pc),a0
 move.l $32fb4,(a0)
 move.l $32fb8,6(a0)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d1/a0-a1
 jmp '''+cont+'\n ELSE\n'+rest+' ENDC\n'
 s=s[:m.start(1)]+new+s[m.end(1):]
# Fold axis selection and the general heading wrapper into each hook. The
# unchanged Step20Delta helper still owns signed division and carry semantics.
for addr,axis in [('678de',0),('67900',1),('67948',0),('67976',1)]:
 m=re.search(r'(?m)^heading_'+addr+r':\n(.*?)(?=^[A-Za-z_]\w*:)',s,re.S);old=m[1];guard,rest=old.split(' ENDC\n',1);native='$32fb4' if axis==0 else '$32fb8'
 new=guard+f''' ENDC
 IFD FF1_LEAN_PLAYER
 movem.l d0-d2/a0,-(sp)
 move.w ccr,-(sp)
 lea heading_shadow+{axis*6}(pc),a0
 move.l {native},(a0)
 addq.l #4,a0
 bsr.w FF1Step20Delta
 tst.l d1
 bne.b .unchanged
 add.l d0,-4(a0)
.unchanged:
 move.l -4(a0),{native}
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a0
 jmp ${int(addr,16)+6:x}
 ELSE
'''+rest+' ENDC\n';s=s[:m.start(1)]+new+s[m.end(1):]
p.write_text(s)
for n in ('build_step5_b4.py','capture_step5_b4_matrix.py','profile_step5_b4.py'):
 p=Path('tmp/dev/tools')/n;p.write_text(p.read_text().replace('b4-v3','b4-v4'))
