from pathlib import Path
import shutil,subprocess,sys,json
r=Path(__file__).resolve().parents[1];src=r/'tmp/build/render-h13-gauge-source';shutil.copytree(r/'tmp/build/render-h10-grid-source',src,dirs_exist_ok=True)
extra='''
H13Install:
 tst.w H13Control(pc)
 beq.b .done
 lea H13Gauge(pc),a0
 move.l a0,$6bd68
 move.l a0,$6bdb8
.done:
 rts
H13Gauge:
 cmpi.w #1,42(sp)
 bne.w .native
 cmpi.w #3,46(sp)
 bne.w .native
 cmpi.w #12,34(sp)
 bne.w .native
 cmpi.w #6,50(sp)
 bne.w .native
 tst.w 54(sp)
 bne.w .native
 tst.w 10(sp)
 bne.w .native
 tst.w 14(sp)
 bne.w .native
 tst.w $1c1e8
 beq.w .native
 movem.l d0-d7/a0-a6,-(sp)
 lea 60(sp),a6
 move.l 20(a6),a2
 cmpa.l #$1fdb8,a2
 bne.w .fallback
 move.w 38(a6),d0
 cmpi.w #68,d0
 beq.b .width
 cmpi.w #40,d0
 bne.w .fallback
.width:
 move.w 26(a6),d1
 cmpi.w #68,d1
 bhi.w .fallback
 move.w 30(a6),d2
 cmpi.w #23,d2
 bhi.w .fallback
 move.w 18(a6),d3
 lsl.w #4,d3
 cmp.w d0,d3
 blo.w .fallback
 tst.w $1c1b4
 bne.b .owned
 jsr $2a260
.owned:
 jsr $2a130
 move.w d1,d5
 andi.w #15,d5
 lsr.w #4,d1
 add.w d1,d1
 mulu.w #24,d2
 add.w d1,d2
 move.w d0,d6
 add.w d5,d6
 subq.w #1,d6
 move.w d6,d7
 lsr.w #4,d7
 andi.w #15,d6
 moveq #15,d4
 sub.w d6,d4
 moveq #-1,d6
 lsl.w d4,d6
 moveq #0,d3
.plane:
 move.l 4(a6),a0
 move.l (a2)+,a1
 adda.w d2,a1
 moveq #0,d0
 move.w d7,d4
.word:
 swap d0
 move.w (a0)+,d0
 move.l d0,d1
 lsr.l d5,d1
 tst.w d3
 bne.b .colour
 moveq #0,d1
.colour:
 moveq #-1,d0
 cmp.w d7,d4
 bne.b .notfirst
 lsr.w d5,d0
.notfirst:
 tst.w d4
 bne.b .notlast
 and.w d6,d0
.notlast:
 and.w d0,d1
 not.w d0
 and.w (a1),d0
 or.w d0,d1
 move.w d1,(a1)+
 ; Keep the preceding unshifted source word for the next shift.
 moveq #0,d0
 move.w -2(a0),d0
 dbra d4,.word
 addq.w #1,d3
 cmpi.w #3,d3
 bne.b .plane
 movem.l (sp)+,d0-d7/a0-a6
 andi #$ef,ccr
 jmp $24d70
.fallback:
 movem.l (sp)+,d0-d7/a0-a6
.native:
 jmp $24ae0
H13Control: dc.w 1
'''
f=src/'FerrariFormulaOne/Fine.s';s=f.read_text().replace(' bsr.l FF1RenderInstallClear',' bsr.l H13Install\n bsr.l FF1RenderInstallClear').replace(' include "RenderClear.s"',extra+'\n include "RenderClear.s"');f.write_text(s)
b=r/'tmp/build/render-h13-gauge';subprocess.run([sys.executable,str(src/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(b)],check=True)
c=b.with_name(b.name+'-control');shutil.copytree(b,c,dirs_exist_ok=True);m=json.loads((b/'build.json').read_text());at=32+m['payloads']['fine']['offset']+m['payloads']['fine']['symbols']['H13Control'];d=bytearray((c/'FerrariFormulaOne.slave').read_bytes());assert d[at:at+2]==b'\0\1';d[at:at+2]=b'\0\0';(c/'FerrariFormulaOne.slave').write_bytes(d)
