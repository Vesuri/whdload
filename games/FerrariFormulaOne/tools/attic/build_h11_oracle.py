from pathlib import Path
import shutil,subprocess,sys,json
r=Path(__file__).resolve().parents[1];src=r/'tmp/build/render-h11-v2-oracle-source';shutil.copytree(r/'tmp/build/render-h11-v2-matched-source',src,dirs_exist_ok=True)
cases=[dict(glyph=i,fg=7,bg=0,x=32,y=3,ready=1) for i in range(28)]
cases += [dict(glyph=8,fg=i,bg=0,x=32,y=3,ready=int(i==7)) for i in range(8)]
cases += [dict(glyph=9,fg=7,bg=i,x=32,y=3,ready=int(i==0)) for i in range(8)]
cases += [dict(glyph=10,fg=7,bg=0,x=x,y=y,ready=0) for x,y in [(31,3),(32,4),(30,2)]]
asm='''
H11Oracle:
 movem.l d0-d7/a0-a6,-(sp)
 move.w ccr,-(sp)
 tst.l H11OracleChecked(pc)
 bne.l H11OracleReturn
 jsr $2a260
 move.w #1,$1c1b4
 jsr $2a130
 lea H11Saved(pc),a0
 move.l $226cd,(a0)+
 move.l $226d1,(a0)+
 move.l $23608,(a0)+
 move.l $23610,(a0)+
 move.w FF1FlagGraphic(pc),(a0)+
 lea FF1FlagGraphic(pc),a0
 clr.w (a0)
 lea (H11Initial.l,pc),a0
 bsr.l H11SaveScreen
 lea H11Cases(pc),a5
 moveq #CASES-1,d7
.case:
 lea (H11Initial.l,pc),a0
 bsr.l H11RestoreScreen
 move.b (a5),d0
 lea $226cd,a0
 moveq #6,d1
.digits:
 move.b d0,(a0)+
 dbra d1,.digits
 move.w 2(a5),$23608
 move.w 4(a5),$2360a
 move.w 6(a5),$23610
 move.w 8(a5),$23612
 movem.l d7/a5,-(sp)
 bsr.l FF1RenderPresentHUD
 jsr $2a130
 lea (H11Expected.l,pc),a0
 bsr.l H11SaveScreen
 lea (H11Initial.l,pc),a0
 bsr.l H11RestoreScreen
 bsr.l FF1RenderPrepareClock
 movem.l (sp)+,d7/a5
 moveq #0,d0
 move.w FF1RenderClockReady(pc),d0
 cmp.w 10(a5),d0
 bne.l H11OracleBad
 lea H11ReadyCount(pc),a0
 add.l d0,(a0)
 movem.l d7/a5,-(sp)
 bsr.l FF1RenderOverlapHUD
 jsr $2a130
 tst.w FF1RenderClockReady(pc)
 bne.l H11OracleBad
 lea (H11Expected.l,pc),a0
 bsr.l H11CompareScreen
 movem.l (sp)+,d7/a5
 lea H11OracleChecked(pc),a0
 addq.l #1,(a0)
 lea 12(a5),a5
 dbra d7,.case
 lea (H11Initial.l,pc),a0
 bsr.l H11RestoreScreen
 lea H11Saved(pc),a0
 move.l (a0)+,$226cd
 move.l (a0)+,$226d1
 move.l (a0)+,$23608
 move.l (a0)+,$23610
 lea FF1FlagGraphic(pc),a1
 move.w (a0)+,(a1)
 jsr $2a270
 clr.w $1c1b4
H11OracleDone:
 nop
H11OracleReturn:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 rts
H11OracleBad:
 lea H11OracleError(pc),a0
 move.l #1,(a0)
 bra.b H11OracleBad
H11SaveScreen:
 movem.l d0-d2/a1-a2,-(sp)
 move.l $226ae,a2
 moveq #2,d1
.plane:
 move.l (a2)+,a1
 move.w #2399,d0
.copy:
 move.l (a1)+,(a0)+
 dbra d0,.copy
 dbra d1,.plane
 movem.l (sp)+,d0-d2/a1-a2
 rts
H11RestoreScreen:
 movem.l d0-d2/a1-a2,-(sp)
 move.l $226ae,a2
 moveq #2,d1
.plane:
 move.l (a2)+,a1
 move.w #2399,d0
.copy:
 move.l (a0)+,(a1)+
 dbra d0,.copy
 dbra d1,.plane
 movem.l (sp)+,d0-d2/a1-a2
 rts
H11CompareScreen:
 movem.l d0-d2/a1-a2,-(sp)
 move.l $226ae,a2
 moveq #2,d1
.plane:
 move.l (a2)+,a1
 move.w #2399,d0
.copy:
 cmpm.l (a0)+,(a1)+
 bne.l H11OracleBad
 dbra d0,.copy
 dbra d1,.plane
 movem.l (sp)+,d0-d2/a1-a2
 rts
H11Cases:
'''.replace('CASES',str(len(cases)))
for c in cases:asm+=' dc.w '+','.join(map(str,[c['glyph']*256,c['fg'],c['bg'],c['x'],c['y'],c['ready']]))+'\n'
asm+='H11OracleChecked: dc.l 0\nH11OracleError: dc.l 0\nH11ReadyCount: dc.l 0\nH11Saved: ds.b 18\n'
p=src/'FerrariFormulaOne/Fine.s';s=p.read_text().replace(' bsr.l B8Draw\n',' bsr.l B8Draw\n bsr.l H11Oracle\n').replace(' include "RenderOverlap.s"',asm+'\n include "RenderOverlap.s"');s+='\nH11Initial: ds.b 28800\nH11Expected: ds.b 28800\n';p.write_text(s)
b=r/'tmp/build/render-h11-v2-oracle';subprocess.run([sys.executable,str(src/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(b)],check=True);(b/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
s=(r/'tools/test_h13_oracle.py').read_text().replace('H13','H11').replace('h13','h11');(r/'tools/test_h11_oracle.py').write_text(s)
