from pathlib import Path
import shutil,subprocess,sys,json
r=Path(__file__).resolve().parents[1];src=r/'tmp/build/render-h10-oracle-source';shutil.copytree(r/'tmp/build/render-h10-matched-source',src,dirs_exist_ok=True)
cases=[(h,i,p,c) for p in (0,1) for h in ((1,17,100,200) if p==0 else (17,)) for i in range(3) for c in range(32)]
asm='''
H10Oracle:
 tst.l H10OracleChecked(pc)
 bne.w H10OracleReturn
 movem.l d0-d7/a0-a6,-(sp)
 link a6,#-8
 lea H10OracleCases(pc),a0
 lea H10OracleCase(pc),a1
 move.l a0,(a1)
.loop:
 bsr.w H10OracleSeed
 move.l H10OracleCase(pc),a4
 move.w 2(a4),-2(a6)
 move.w (a4),d0
 lsl.w #6,d0
 ori.w #24,d0
 move.l $226ae,a0
 move.l (a0),a1
 move.l a1,$dff054
 move.w 6(a4),ccr
 move.w d0,$dff058
 move.w ccr,d6
 jsr $2a130
 lea H10OracleExpectedCCR(pc),a0
 move.w d6,(a0)
 move.l $226ae,a0
 move.l (a0),a0
 lea H10OraclePixels(pc),a1
 move.w #2399,d0
.save:
 move.l (a0)+,(a1)+
 dbra d0,.save
 bsr.w H10OracleSeed
 move.l H10OracleCase(pc),a4
 move.w 2(a4),-2(a6)
 move.w (a4),d0
 lsl.w #6,d0
 ori.w #24,d0
 ori.l #$a5000000,d0
 move.l $226ae,a0
 move.l (a0),a1
 tst.w 4(a4)
 bne.b .top
 move.w 6(a4),ccr
 bsr.l FF1RenderClearBottom
 bra.b .returned
.top:
 move.w 6(a4),ccr
 bsr.l FF1RenderClearTop
.returned:
 move.w ccr,d6
 cmp.w H10OracleExpectedCCR(pc),d6
 bne.w H10OracleBad
 ; Registers used for inputs must be preserved, including high D0 bits.
 cmpi.l #$a5000000,d0
 blo.w H10OracleBad
 move.w (a4),d1
 lsl.w #6,d1
 ori.w #24,d1
 cmp.w d0,d1
 bne.w H10OracleBad
 move.l $226ae,a0
 cmpa.l (a0),a1
 bne.w H10OracleBad
 jsr $2a130
 move.l $226ae,a0
 move.l (a0),a0
 lea H10OraclePixels(pc),a1
 move.w #2399,d0
.compare:
 cmpm.l (a0)+,(a1)+
 bne.w H10OracleBad
 dbra d0,.compare
 lea H10OracleChecked(pc),a0
 addq.l #1,(a0)
 cmpi.l #COUNT,(a0)
 beq.b H10OracleDone
 lea H10OracleCase(pc),a0
 addq.l #8,(a0)
 bra.w .loop
H10OracleDone:
 unlk a6
 movem.l (sp)+,d0-d7/a0-a6
H10OracleReturn:
 rts
H10OracleBad:
 lea H10OracleError(pc),a0
 move.l #1,(a0)
 bra.s H10OracleBad
H10OracleSeed:
 jsr $2a130
 move.l $226ae,a0
 move.l (a0),a1
 move.l #$a55a3cc3,d1
 move.w #2399,d0
.seed:
 move.l d1,(a1)+
 not.l d1
 dbra d0,.seed
 clr.w $dff042
 clr.w $dff066
 move.l #-1,$dff044
 move.l H10OracleCase(pc),a0
 move.w 2(a0),d0
 tst.w 4(a0)
 bne.b .top
 cmpi.w #2,d0
 beq.b .ones
 bra.b .zero
.top:
 tst.w d0
 beq.b .ones
.zero:
 move.w #$100,$dff040
 rts
.ones:
 move.w #$1ff,$dff040
 rts
H10OracleChecked: dc.l 0
H10OracleError: dc.l 0
H10OracleCase: dc.l 0
H10OracleExpectedCCR: dc.w 0
H10OraclePixels: ds.b 9600
H10OracleCases:
'''.replace('COUNT',str(len(cases)))+'\n'.join(' dc.w '+','.join(map(str,x)) for x in cases)+'\n'
p=src/'FerrariFormulaOne/Fine.s';s=p.read_text().replace(' bsr.l B8Draw\n',' bsr.l B8Draw\n bsr.l H10Oracle\n');s=s.replace(' include "RenderClear.s"',asm+'\n include "RenderClear.s"');p.write_text(s)
out=r/'tmp/build/render-h10-oracle';subprocess.run([sys.executable,str(src/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(out)],check=True);(out/'cases.json').write_text(json.dumps(cases))
s=(r/'tools/test_h5_oracle.py').read_text().replace('h5-oracle','h10-oracle').replace('H5Oracle','H10Oracle');a=s.index(" cmd('monitor warp 0');cmd('delete');cmd(f'break *{probe+sy[\"H5BenchStart\"]}")
z=s.index(" report['status']='passed'",a);s=s[:a]+s[z:];(r/'tools/test_h10_oracle.py').write_text(s)
