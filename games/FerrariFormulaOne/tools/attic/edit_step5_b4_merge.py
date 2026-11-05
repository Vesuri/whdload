from pathlib import Path
import re
p=Path('Games/FerrariFormulaOne_UpdateHooks.s');s=p.read_text()
# The six displaced instructions remain in place, with their signatures still
# checked. Merge callback work at the end of each straight-line load/store block.
for name in ('velocity_671e6','velocity_6721c','bridge_6720e','velocity_685a6','velocity_68576','bridge_68546'):
 pat=r' lea \('+name+r'\.l,pc\),a[01]\n move.w #\$4ef9,\$[0-9a-f]+\n move.l a[01],\$[0-9a-f]+\n';m=re.search(pat,s);assert m,name
 s=s[:m.start()]+' IFND FF1_PLAYER_HOOKS\n'+m[0]+' ENDC\n'+s[m.end():]
for name,calls in [('heading_67280',' bsr.w velocity_load\n lea position_shadow(pc),a0\n bsr.w bridge_load\n bsr.w velocity_speed_load\n'),('heading_6860e',' bsr.w velocity_store\n lea position_shadow(pc),a0\n bsr.w bridge_store\n bsr.w velocity_speed_store\n')]:
 pat=r'(?m)^'+name+r':\n(.*?)(?=^[A-Za-z_]\w*:)';m=re.search(pat,s,re.S);old=m[1]
 new=old.replace('movem.l d0/a0,-(sp)','movem.l d0-d2/a0-a1,-(sp)').replace('movem.l (sp)+,d0/a0','movem.l (sp)+,d0-d2/a0-a1')
 new=new.replace(' IFD FF1_PLAYER_HOOKS\n lea (heading_shadow.l,pc),a0',' IFD FF1_PLAYER_HOOKS\n ; Shared save frame for the adjacent native state loads/stores.\n'+calls+' lea (heading_shadow.l,pc),a0')
 assert new!=old;s=s[:m.start(1)]+new+s[m.end(1):]
# The lean feedback callback contains only checks; native store remains.
pat=r' lea \(velocity_679fe.l,pc\),a0\n move.w #\$4ef9,\$679fe\n move.l a0,\$67a00\n';m=re.search(pat,s);assert m
s=s[:m.start()]+' IFND FF1_LEAN_PLAYER\n'+m[0]+' ENDC\n'+s[m.end():]
# Fuel conversion clobbers only D0 (native output), D1 and A1. The displaced
# SUB sets all condition codes, so no incoming CCR save is needed here.
m=re.search(r'(?m)^fuel_6d164:\n(.*?)(?=^[A-Za-z_]\w*:)',s,re.S);old=m[1];guard,body=old.split(' ENDC\n',1)
new=guard+''' ENDC
 IFD FF1_LEAN_PLAYER
 movem.l d1/a1,-(sp)
 lea fuel_remainders(pc),a1
 bsr.w FF1Wear20Delta
 movem.l (sp)+,d1/a1
 dc.w $9190,$2d40,$fffc
 jmp $6d16a
 ELSE
'''+body+' ENDC\n';s=s[:m.start(1)]+new+s[m.end(1):]
# Lean event eligibility needs no register save frame or record callback.
for name,native,tail in [('events_6d5f2','$6ea3e',''),('events_6d67e','$6ee70',' dc.w $588f\n')]:
 m=re.search(r'(?m)^'+name+r':\n(.*?)(?=^[A-Za-z_]\w*:)',s,re.S);old=m[1];guard,body=old.split(' ENDC\n',1)
 new=guard+f''' ENDC
 IFD FF1_LEAN_PLAYER
 move.w ccr,-(sp)
 tst.w events_pulse(pc)
 beq.b .skip
 move.w (sp)+,ccr
 jsr {native}
{tail} jmp $6d684
.skip:
 move.w (sp)+,ccr
{tail} jmp $6d684
 ELSE
'''+body+' ENDC\n';s=s[:m.start(1)]+new+s[m.end(1):]
for name,mask in [('velocity_6e2ae','d0-d2/a0-a2/a4'),('fine_bounds','d0-d1/d4/a0-a1'),('steering_6773c','d0-d6/a0/a5')]:
 m=re.search(r'(?m)^'+name+r':\n(.*?)(?=^[A-Za-z_]\w*:)',s,re.S);old=m[1];new=old
 if name=='velocity_6e2ae':new=new.replace(' move.l d0,d7\n',' IFND FF1_LEAN_PLAYER\n move.l d0,d7\n ENDC\n')
 for src,dst in [('movem.l d0-d7/a0-a6,-(sp)',f'movem.l {mask},-(sp)'),('movem.l (sp)+,d0-d7/a0-a6',f'movem.l (sp)+,{mask}')]:
  new=new.replace(' '+src,' IFD FF1_LEAN_PLAYER\n '+dst+'\n ELSE\n '+src+'\n ENDC')
 s=s[:m.start(1)]+new+s[m.end(1):]
p.write_text(s)
for n in ('build_step5_b4.py','capture_step5_b4_matrix.py','profile_step5_b4.py'):
 p=Path('tmp/dev/tools')/n;p.write_text(p.read_text().replace('b4-v2','b4-v3'))
