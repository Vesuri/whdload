from pathlib import Path
import shutil,subprocess,sys,json
r=Path(__file__).resolve().parents[1];src=r/'tmp/build/render-h13-oracle-source';shutil.rmtree(src);shutil.copytree(r/'tmp/build/render-h13-matched-source',src)
old=(r/'tmp/build/render-h13-gauge-oracle-source/FerrariFormulaOne/Fine.s').read_text();asm=old[old.index('H13Oracle:\n'):old.index(' include "RenderClear.s"')];asm=asm.replace('H13Gauge','FF1RenderGaugeStrip')
# Compare returned CCR and all D/A registers directly with the native call.
asm=asm.replace(' bsr.w H13OracleDraw\n jsr $2a130', ' bsr.w H13OracleDraw\n jsr $2a130')
asm=asm.replace('.call:\n tst.w H13OracleArm(pc)', '.call:\n tst.w H13OracleArm(pc)')
asm=asm.replace(' bsr.l FF1RenderGaugeStrip\n bra.b .done', ' bsr.l FF1RenderGaugeStrip\n move.w ccr,-(sp)\n movem.l d0-d7/a0-a6,-(sp)\n lea H13OracleRegisters(pc),a0\n lea (sp),a1\n moveq #29,d0\n.regcmp:\n cmpm.w (a0)+,(a1)+\n bne.w H13OracleBad\n dbra d0,.regcmp\n move.w (a1),d0\n cmp.w (a0),d0\n bne.w H13OracleBad\n movem.l (sp)+,d0-d7/a0-a6\n move.w (sp)+,ccr\n bra.b .done')
asm=asm.replace(' jsr $24ae0\n.done:', ' jsr $24ae0\n move.w ccr,-(sp)\n movem.l d0-d7/a0-a6,-(sp)\n lea H13OracleRegisters(pc),a0\n lea (sp),a1\n moveq #30,d0\n.regsave:\n move.w (a1)+,(a0)+\n dbra d0,.regsave\n movem.l (sp)+,d0-d7/a0-a6\n move.w (sp)+,ccr\n.done:')
asm=asm.replace('.call:\n tst.w H13OracleArm(pc)', '.call:\n move.l #$11223344,d0\n move.l d0,d1\n move.l d0,d2\n move.l d0,d3\n move.l d0,d4\n move.l d0,d5\n move.l d0,d6\n move.l d0,d7\n move.l d0,a0\n move.l d0,a1\n move.l d0,a2\n move.l d0,a3\n move.l d0,a4\n move.l d0,a5\n move.w #$1f,ccr\n tst.w H13OracleArm(pc)')
asm=asm.replace(' dbra d2,.plane\n rts', ' dbra d2,.plane\n lea $255be,a0\n move.l H13OracleCase(pc),a1\n moveq #0,d1\n move.w (a1),d1\n swap d1\n move.w 4(a1),d1\n eori.l #$a53c69f0,d1\n moveq #4,d0\n.pattern1:\n move.w d1,(a0)+\n rol.l #7,d1\n dbra d0,.pattern1\n lea $255da,a0\n moveq #2,d0\n.pattern2:\n move.w d1,(a0)+\n rol.l #7,d1\n dbra d0,.pattern2\n rts')
# Native24ae0 clobbers D0-D7/A0-A5. Both selected callers rebuild all used
# scratch registers before the next call; preserving them is compatible.
# Compare A6/SP/CCR to native and separately prove full input preservation.
a=asm.index(' lea H13OracleRegisters(pc),a0\n lea (sp),a1\n moveq #29,d0');z=asm.index(' movem.l (sp)+,d0-d7/a0-a6',a)
asm=asm[:a]+''' lea H13OracleRegisters(pc),a0
 lea (sp),a1
 move.l sp,d0
 cmp.l H13OracleExpectedSP(pc),d0
 bne.w H13OracleBad
 moveq #13,d1
.regcmp:
 move.l (a1)+,d0
 cmpi.l #$11223344,d0
 bne.w H13OracleBad
 dbra d1,.regcmp
 move.l (a1)+,d0
 cmp.l 56(a0),d0
 bne.w H13OracleBad
 move.w (a1),d0
 cmp.w 60(a0),d0
 bne.w H13OracleBad
'''+asm[z:]
asm=asm.replace(' lea H13OracleRegisters(pc),a0\n lea (sp),a1\n moveq #30,d0', ' lea H13OracleExpectedSP(pc),a0\n move.l sp,(a0)\n lea H13OracleRegisters(pc),a0\n lea (sp),a1\n moveq #30,d0')
asm+='\nH13OracleRegisters: ds.b 62\nH13OracleExpectedSP: dc.l 0\n'

# Expose actual fast-path execution, test-only, after the synchronization point.
p=src/'FerrariFormulaOne/RenderGauges.s';s=p.read_text().replace(' jsr $2a130\n move.w d1,d5',' jsr $2a130\n lea H13GaugeCalls(pc),a0\n addq.l #1,(a0)\n move.w d1,d5');s+='\nH13GaugeCalls: dc.l 0\n';p.write_text(s)
p=src/'FerrariFormulaOne/Fine.s';s=p.read_text().replace(' bsr.l B8Draw\n',' bsr.l B8Draw\n bsr.l H13Oracle\n').replace(' include "RenderClear.s"',asm+'\n include "RenderClear.s"');p.write_text(s)
b=r/'tmp/build/render-h13-oracle';subprocess.run([sys.executable,str(src/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(b)],check=True);shutil.copy(r/'tmp/build/render-h13-gauge-oracle/cases.json',b/'cases.json')
