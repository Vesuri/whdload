from pathlib import Path
import shutil,subprocess,sys,json
r=Path(__file__).resolve().parents[1]
s=(r/'tools/build_drive_matched.py').read_text().replace('drive-matched','render-h11-sky-probe-matched')
exec(compile(s,str(r/'tools/build_drive_matched.py'),'exec'))
src=r/'tmp/build/render-h11-sky-probe-matched-source'
f=src/'FerrariFormulaOne_FullPresentation.s';s=f.read_text().replace('B8_6573a:\n','B8_6573a:\n IFD FF1_FINE_TEXT\n bsr.l H11Flag\n ENDC\n').replace('B8_6574a:\n','B8_6574a:\n IFD FF1_FINE_TEXT\n bsr.l H11Clock\n ENDC\n').replace(' bsr.w FF1RenderPresentHUD',' bsr.l H11LateHUD');f.write_text(s)
f=src/'FerrariFormulaOne/RenderBitmap.s';s=f.read_text().replace('.owned:\n jsr $2a130','.owned:\n tst.w H11Active(pc)\n bne.b .h11_async\n jsr $2a130\n.h11_async:');f.write_text(s)
f=src/'FerrariFormulaOne/Fine.s';s=f.read_text();extra='''
; Diagnostic only: test the upper bound of clock/last-wheel-blit overlap.
H11Flag:
 tst.w H11Control(pc)
 beq.b .done
 move.w ccr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 move.l $226b2,-(sp)
 move.l $226ae,$226b2
 bsr.l FF1PresentFlag
 move.l (sp)+,$226b2
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
.done:
 rts
H11Clock:
 tst.w H11Control(pc)
 beq.b .done
 move.w ccr,-(sp)
 movem.l d0-d7/a0-a6,-(sp)
 move.l $226b2,-(sp)
 move.l $226ae,$226b2
 lea H11Active(pc),a0
 move.w #1,(a0)
 bsr.l FF1PresentClock
 lea H11Active(pc),a0
 clr.w (a0)
 move.l (sp)+,$226b2
 movem.l (sp)+,d0-d7/a0-a6
 move.w (sp)+,ccr
.done:
 rts
H11LateHUD:
 tst.w H11Control(pc)
 beq.l FF1RenderPresentHUD
 rts
H11Control: dc.w 1
H11Active: dc.w 0
''';s=s.replace(' include "RenderRoad.s"',extra+'\n include "RenderRoad.s"');f.write_text(s)
s=(r/'tools/build_hi25_fixtures.py').read_text().replace('render-h5-matched-source','render-h11-sky-probe-matched-source').replace('render-hi25-','render-h11-sky-probe-')
sys.argv=['build_hi25_fixtures.py','grid'];exec(compile(s,str(r/'tools/build_hi25_fixtures.py'),'exec'))
b=r/'tmp/build/render-h11-sky-probe-grid';o=b.with_name(b.name+'-control');shutil.copytree(b,o,dirs_exist_ok=True);m=json.loads((b/'build.json').read_text());at=32+m['payloads']['fine']['offset']+m['payloads']['fine']['symbols']['H11Control'];p=o/'FerrariFormulaOne.slave';d=bytearray(p.read_bytes());assert d[at:at+2]==b'\0\1';d[at:at+2]=b'\0\0';p.write_bytes(d)
