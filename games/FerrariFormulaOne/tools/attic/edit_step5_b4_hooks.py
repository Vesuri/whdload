from pathlib import Path
import re
p=Path('Games/FerrariFormulaOne_UpdateHooks.s');s=p.read_text()
s=s.replace('FF1UpdateWorkspace macro',''' IFD FF1_PLAYER_HOOKS
 IFND FF1_PLAN_B
 fail "FF1_PLAYER_HOOKS requires FF1_PLAN_B"
 ENDC
 IFND VERIFY
FF1_LEAN_PLAYER equ 1
 ENDC
 ENDC

FF1UpdateWorkspace macro''',1)
# Specialize the scalar sites; each proposed native result is consumed at its
# original point. Branches and engine side effects between them remain native.
for addr in ['672f0','673fc','67426','67438','6744a','67476','675c0','6766c','6768e','676e0']:
 label='velocity_'+addr;pat=r'(?m)^'+label+r':\n(.*?)(?=^[A-Za-z_]\w*:)';m=re.search(pat,s,re.S);old=m[1];cont=int(addr,16)+6
 new=f''' IFD FF1_LEAN_PLAYER
 tst.w $32fbc
 bne.b .native
 move.w d0,$32fbe
 movem.l d1/a0,-(sp)
 move.w ccr,-(sp)
 lea speed_work(pc),a0
 bsr.w FF1SpeedRate20
 move.w (a0),d0
 ext.l d0
 move.w d0,$32fbe
 move.w (sp)+,ccr
 movem.l (sp)+,d1/a0
 jmp ${cont:x}
.native:
 move.w d0,$32fbe
 jmp ${cont:x}
 ELSE
'''+old+' ENDC\n'
 s=s[:m.start(1)]+new+s[m.end(1):]
# Same exact conversion as wear_sample; omit tracing arguments and broad saves.
for addr,pre,post,out in [('6de74',' dc.w $4c01,$0800,$4e71','',0),('6defa',' dc.w $4c01,$0800,$4e71','',0),('6de96',' dc.w $2236,$08d8',' dc.w $9390',1),('6ded4',' dc.w $2236,$08d8',' dc.w $9390',1),('6df2a',' dc.w $2236,$08d8,$e381',' dc.w $9390',1)]:
 pat=r'(?m)^wear_'+addr+r':\n(.*?)(?=^[A-Za-z_]\w*:)';m=re.search(pat,s,re.S);old=m[1]
 guard,body=old.split(' ENDC\n',1)
 cont=re.findall(r'jmp (\$\w+)',body)[-1]
 body=f'''{pre}
 movem.l d0-d2/a1,-(sp)
 move.w ccr,-(sp)
 move.l a0,d2
 subi.l #$66c52,d2
 lsr.l #2,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
'''+(' move.l d1,d0\n' if out else '')+f''' bsr.w FF1Wear20Delta
 move.l d0,{2+out*4}(sp)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d2/a1
{post}
 jmp {cont}
'''
 s=s[:m.start(1)]+guard+' ENDC\n IFD FF1_LEAN_PLAYER\n'+body+' ELSE\n'+old.split(' ENDC\n',1)[1]+' ENDC\n'+s[m.end(1):]
# Minimum lean callback masks; D0/D1 stay first wherever the old callback
# writes its result into the saved frame. VERIFY retains its wider trace ABI.
masks={
'velocity_671e6':'d0-d2/a0-a1','velocity_685a6':'d0/a0','velocity_67bcc':'d0-d2/a0-a2',
'velocity_6dc96':'d0-d2/a0-a2/a4','velocity_6dd44':'d0-d1/d7/a4','velocity_6e084':'d0-d2/a4',
'velocity_6712e':'d0-d1/a0',
'velocity_6721c':'d0/a0-a1','velocity_68576':'d0/a0-a1',
'heading_67280':'d0/a0','heading_6860e':'d0/a0',
'heading_67948':'d0-d2/d4-d5/a0/a2-a3','heading_67976':'d0-d2/d4-d5/a0/a2-a3',
'heading_67326':'d0-d1/a0','heading_683ac':'d0-d1/a0',
'fine_advance':'d0-d2/a0/a2-a3/a5','fine_boundary':'d0-d1/d4/a0-a1',
}
# Remove redundant D7 copies from callbacks that never consume it.
remove_d7=['velocity_671e6','velocity_685a6','velocity_67bcc','velocity_6dc96','velocity_6e084','velocity_6721c','velocity_68576']
# Bridge sync/reset hooks clobber A0/D0 only, plus A1 for load's crossing reset.
for name in re.findall(r'^bridge_[0-9a-f]+:',s,re.M):
 m=re.search(r'(?m)^'+name+r'\n(.*?)(?=^[A-Za-z_]\w*:)',s,re.S)
 if m and re.search(r'bsr.w bridge_(load|store|sync_x|sync_z|reset_x|reset_z)\n',m[1]):masks[name[:-1]]='d0/a0-a1' if 'bsr.w bridge_load' in m[1] else 'd0/a0'
for name,mask in masks.items():
 m=re.search(r'(?m)^'+name+r':\n(.*?)(?=^[A-Za-z_]\w*:)',s,re.S)
 if not m:continue
 old=m[1];new=old
 if name in remove_d7:new=new.replace(' move.l d0,d7\n',' IFND FF1_LEAN_PLAYER\n move.l d0,d7\n ENDC\n')
 if name.startswith('heading_') and name not in ('heading_67948','heading_67976'):
  new=new.replace(' move.l d0,d4\n',' IFND FF1_LEAN_PLAYER\n move.l d0,d4\n ENDC\n')
 for src,dst in [('movem.l d0-d7/a0-a6,-(sp)',f'movem.l {mask},-(sp)'),('movem.l (sp)+,d0-d7/a0-a6',f'movem.l (sp)+,{mask}')]:
  new=new.replace(' '+src,' IFD FF1_LEAN_PLAYER\n '+dst+'\n ELSE\n '+src+'\n ENDC')
 s=s[:m.start(1)]+new+s[m.end(1):]
p.write_text(s)
p=Path('tmp/dev/tools/build_step5_b4.py');p.write_text(p.read_text().replace('step5-b4-v1','step5-b4-v2'))
