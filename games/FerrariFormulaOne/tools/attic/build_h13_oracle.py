from pathlib import Path
import shutil,subprocess,sys,json
r=Path(__file__).resolve().parents[1];src=r/'tmp/build/render-h13-oracle-source';shutil.copytree(r/'tmp/build/render-h13-probe-source',src,dirs_exist_ok=True)
# Native routine supplies all register setup, shifts, clipping and three planes.
cases=[(x,y) for y in (60,120) for x in list(range(16))+[-193,-192,-191,-33,-32,-31,-17,-16,-15,-1,191,192,193,367,368,369,383,384]]
asm='''
H13Oracle:
 tst.l H13OracleChecked(pc)
 bne.w H13OracleReturn
 movem.l d0-d7/a0-a6,-(sp)
 lea H13OracleCases(pc),a0
 lea H13OracleCase(pc),a1
 move.l a0,(a1)
.loop:
 bsr.w H13OracleSeed
 lea H13OracleArm(pc),a0
 clr.w (a0)
 bsr.w H13OracleDraw
 jsr $2a130
 move.l $226ae,a2
 lea H13OraclePixels(pc),a1
 moveq #2,d2
.saveplane:
 move.l (a2)+,a0
 move.w #2399,d0
.save:
 move.l (a0)+,(a1)+
 dbra d0,.save
 dbra d2,.saveplane
 bsr.w H13OracleSeed
 lea H13OracleArm(pc),a0
 move.w #1,(a0)
 bsr.w H13OracleDraw
 jsr $2a130
 move.l $226ae,a2
 lea H13OraclePixels(pc),a1
 moveq #2,d2
.compareplane:
 move.l (a2)+,a0
 move.w #2399,d0
.compare:
 cmpm.l (a0)+,(a1)+
 bne.w H13OracleBad
 dbra d0,.compare
 dbra d2,.compareplane
 lea H13OracleChecked(pc),a0
 addq.l #1,(a0)
 cmpi.l #COUNT,(a0)
 beq.b H13OracleDone
 lea H13OracleCase(pc),a0
 addq.l #4,(a0)
 bra.w .loop
H13OracleDone:
 movem.l (sp)+,d0-d7/a0-a6
H13OracleReturn:
 rts
H13OracleBad:
 lea H13OracleError(pc),a0
 move.l #1,(a0)
 bra.s H13OracleBad
H13OracleDraw:
 move.l H13OracleCase(pc),a0
 move.w 2(a0),d0
 ext.l d0
 move.l d0,-(sp)
 move.w (a0),d0
 addi.w #87,d0
 ext.l d0
 move.l d0,-(sp)
 pea $1fdac
 jsr $6ba18
 lea 12(sp),sp
 rts
H13OracleSeed:
 jsr $2a130
 move.l $226ae,a2
 moveq #2,d2
.plane:
 move.l (a2)+,a1
 move.l #$a55a3cc3,d1
 move.w #2399,d0
.seed:
 move.l d1,(a1)+
 not.l d1
 dbra d0,.seed
 dbra d2,.plane
 rts
H13OracleDispatch:
 tst.w H13OracleArm(pc)
 bne.l H13Blit
 move.w d0,$dff058
 rts
H13OracleChecked: dc.l 0
H13OracleError: dc.l 0
H13OracleCase: dc.l 0
H13OracleArm: dc.w 1
H13OraclePixels: ds.b 28800
H13OracleCases:
'''.replace('COUNT',str(len(cases)))+'\n'.join(' dc.w '+','.join(map(str,x)) for x in cases)+'\n'
p=src/'FerrariFormulaOne/Fine.s';s=p.read_text().replace('lea H13Blit(pc),a0','lea H13OracleDispatch(pc),a0').replace(' bsr.l B8Draw\n',' bsr.l B8Draw\n bsr.l H13Oracle\n').replace(' include "RenderClear.s"',asm+'\n include "RenderClear.s"');p.write_text(s)
b=r/'tmp/build/render-h13-oracle';subprocess.run([sys.executable,str(src/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(b)],check=True);(b/'cases.json').write_text(json.dumps(cases))
s=(r/'tools/test_h10_oracle.py').read_text().replace('h10','h13').replace('H10','H13');(r/'tools/test_h13_oracle.py').write_text(s)
