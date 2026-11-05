from pathlib import Path
import shutil,subprocess,sys,json
r=Path(__file__).resolve().parents[1];src=r/'tmp/build/render-h13-probe-source';shutil.copytree(r/'tmp/build/render-h10-grid-source',src,dirs_exist_ok=True)
f=src/'FerrariFormulaOne/Fine.s';s=f.read_text().replace(' bsr.l FF1RenderInstallClear',' bsr.l H13Install\n bsr.l FF1RenderInstallClear');extra='''
H13Install:
 tst.w H13Control(pc)
 beq.b .done
 lea H13Blit(pc),a0
 move.w #$4eb9,$6bbe6
 move.l a0,$6bbe8
.done:
 rts
H13Blit:
 move.w ccr,-(sp)
 movem.l d0-d7/a0-a5,-(sp)
 move.l a0,a2
 move.w -6(a6),d0
 lsl.w #2,d0
 move.l $226ae,a1
 move.l (a1,d0.w),a3
 move.w 14(a6),d0
 ext.l d0
 asr.l #4,d0
 add.w -8(a6),d0
 add.w d0,d0
 adda.w d0,a3
 move.w 18(a6),d0
 muls.w #48,d0
 adda.l d0,a3
 move.l 8(a6),a0
 move.w -6(a6),d1
 lsl.w #2,d1
 move.l 12(a0,d1.w),a1
 move.w -8(a6),d1
 add.w d1,d1
 adda.w d1,a1
 move.w -2(a6),d6
 add.w d6,d6
 move.w -4(a6),d7
 subq.w #1,d7
 moveq #0,d5
 move.w -12(a6),d5
 moveq #0,d2
 moveq #0,d3
.row:
 move.l a2,a4
 move.l a1,a5
 move.w -2(a6),d4
 addq.w #1,d4
 sub.w -8(a6),d4
 sub.w -10(a6),d4
 subq.w #1,d4
 move.w d4,-(sp)
.word:
 moveq #0,d0
 move.w (a4)+,d0
 tst.w d4
 beq.b .last
 cmp.w (sp),d4
 bne.b .mask
 tst.w -8(a6)
 beq.b .mask
.last:
 moveq #0,d0
.mask:
 swap d2
 move.w d0,d2
 move.l d2,d0
 lsr.l d5,d0
 swap d3
 move.w (a5)+,d3
 move.l d3,d1
 lsr.l d5,d1
 tst.w d0
 beq.b .skip
 cmpi.w #-1,d0
 beq.b .opaque
 and.w d0,d1
 not.w d0
 and.w (a3),d0
 or.w d0,d1
.opaque:
 move.w d1,(a3)
.skip:
 addq.l #2,a3
 dbra d4,.word
 move.w (sp)+,d4
 addq.w #1,d4
 add.w d4,d4
 neg.w d4
 adda.w d4,a3
 lea 48(a3),a3
 adda.w d6,a2
 adda.w d6,a1
 dbra d7,.row
 movem.l (sp)+,d0-d7/a0-a5
 move.w (sp)+,ccr
 tst.w d0
 rts
H13Control: dc.w 1
''';s=s.replace(' include "RenderClear.s"',extra+'\n include "RenderClear.s"');f.write_text(s)
b=r/'tmp/build/render-h13-probe';subprocess.run([sys.executable,str(src/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(b)],check=True)
c=b.with_name(b.name+'-control');shutil.copytree(b,c,dirs_exist_ok=True);m=json.loads((b/'build.json').read_text());at=32+m['payloads']['fine']['offset']+m['payloads']['fine']['symbols']['H13Control'];d=bytearray((c/'FerrariFormulaOne.slave').read_bytes());assert d[at:at+2]==b'\0\1';d[at:at+2]=b'\0\0';(c/'FerrariFormulaOne.slave').write_bytes(d)
