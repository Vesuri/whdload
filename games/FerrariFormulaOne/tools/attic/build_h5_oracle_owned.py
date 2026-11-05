from pathlib import Path
import shutil,subprocess,sys,json
r=Path(__file__).resolve().parents[1];g=r.parents[1]/'Games';o=r/'tmp/build/render-h5-oracle-owned-source';o.mkdir(exist_ok=True)
for p in g.glob('FerrariFormulaOne_*.s'):shutil.copy2(p,o/p.name)
shutil.copytree(g/'FerrariFormulaOne',o/'FerrariFormulaOne',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
cases=[]
for font in (0,1):
 for alignment in (0,8):
  for fg in range(8):
   for bg in range(8):cases.append([font,alignment,0,(0,8,376)[(fg+bg)%3],(0,128,207)[fg%3],8,8,fg,bg])
for shift in range(1,8):cases.append([0,0,0,shift,128,8,8,7,0])
for width,height in [(7,8),(9,8),(16,8),(8,4),(8,9)]:cases.append([1,0,0,32,128,width,height,3,4])
asm='''
H5Oracle:
 tst.l H5OracleChecked(pc)
 bne.w H5OracleReturn
 movem.l d0-d7/a0-a6,-(sp)
 jsr $2a130
 jsr $2a260
 move.w #1,$1c1b4
 lea H5OracleCases(pc),a0
 lea H5OracleCase(pc),a1
 move.l a0,(a1)
.loop:
 bsr.w H5OracleFill
 lea FF1RenderBitmapControl(pc),a0
 clr.w (a0)
 bsr.w H5OracleCall
 move.w ccr,d0
 lea H5OracleCCR(pc),a0
 move.w d0,(a0)
 jsr $2a130
 move.l $226ae,a2
 lea H5OraclePixels(pc),a3
 moveq #2,d2
.saveplane:
 move.l (a2)+,a0
 move.w #2579,d0
.save:
 move.l (a0)+,(a3)+
 dbra d0,.save
 dbra d2,.saveplane
 bsr.w H5OracleFill
 lea FF1RenderBitmapControl(pc),a0
 move.w #1,(a0)
 bsr.w H5OracleCall
 move.w ccr,d0
 cmp.w H5OracleCCR(pc),d0
 bne.w H5OracleBad
 jsr $2a130
 move.l $226ae,a2
 lea H5OraclePixels(pc),a3
 moveq #2,d2
.compareplane:
 move.l (a2)+,a0
 move.w #2579,d0
.compare:
 cmpm.l (a0)+,(a3)+
 bne.w H5OracleBad
 dbra d0,.compare
 dbra d2,.compareplane
 lea H5OracleChecked(pc),a0
 addq.l #1,(a0)
 lea H5OracleCase(pc),a0
 addi.l #18,(a0)
 move.l H5OracleChecked(pc),d0
 cmpi.l #COUNT,d0
 blo.w .loop
H5OracleDone:
 jsr $2a270
 clr.w $1c1b4
 movem.l (sp)+,d0-d7/a0-a6
 movem.l d0-d7/a0-a6,-(sp)
 tst.w H5OracleBenchMode(pc)
 bne.b .keep
 move.w #$4a79,$24ae0
 move.l #$1c1b4,$24ae2
.keep:
 bsr.l public_flush
 move.l schedule_context+FF1T_FIELDS(pc),d0
 addq.l #2,d0
.settle:
 cmp.l schedule_context+FF1T_FIELDS(pc),d0
 bhi.b .settle
H5BenchStart:
 lea H5OracleBenchCase(pc),a0
 lea H5OracleCase(pc),a1
 move.l a0,(a1)
 move.w #19999,d7
H5BenchLoop:
 move.l d7,-(sp)
 bsr.w H5OracleCall
 move.l (sp)+,d7
 dbra d7,H5BenchLoop
 jsr $2a130
H5BenchDone:
 movem.l (sp)+,d0-d7/a0-a6
H5OracleReturn:
 rts
H5OracleBad:
 lea H5OracleError(pc),a0
 move.l #1,(a0)
 bra.b H5OracleBad
H5OracleFill:
 move.l $226ae,a2
 moveq #2,d2
.fillplane:
 move.l (a2)+,a0
 move.w #2579,d0
.fill:
 move.l #$5aa56996,(a0)+
 dbra d0,.fill
 dbra d2,.fillplane
 rts
H5OracleCall:
 move.l H5OracleCase(pc),a0
 move.l $216d8,a1
 move.w $216cc,d0
 tst.w (a0)
 beq.b .font
 move.l $21798,a1
 move.w $2178c,d0
.font:
 move.w 16(a0),d1
 ext.l d1
 move.l d1,-(sp)
 move.w 14(a0),d1
 ext.l d1
 move.l d1,-(sp)
 pea 3.w
 move.w 12(a0),d1
 ext.l d1
 move.l d1,-(sp)
 move.w 10(a0),d1
 ext.l d1
 move.l d1,-(sp)
 pea 24.w
 move.w 8(a0),d1
 ext.l d1
 move.l d1,-(sp)
 move.w 6(a0),d1
 ext.l d1
 move.l d1,-(sp)
 move.l $226ae,-(sp)
 ext.l d0
 move.l d0,-(sp)
 move.w 4(a0),d1
 ext.l d1
 move.l d1,-(sp)
 move.w 2(a0),d1
 ext.l d1
 move.l d1,-(sp)
 move.l a1,-(sp)
 jsr $24ae0
 lea 52(sp),sp
 rts
H5OracleCCR: dc.w 0
H5OracleBenchMode: dc.w 1
H5OracleChecked: dc.l 0
H5OracleError: dc.l 0
H5OracleCase: dc.l 0
H5OracleBenchCase: dc.w 0,0,0,8,128,8,8,7,0
H5OracleCases:
'''.replace('COUNT',str(len(cases)))+'\n'.join(' dc.w '+','.join(map(str,c)) for c in cases)+'\nH5OraclePixels: ds.b 30960\n'
p=o/'FerrariFormulaOne/Fine.s';s=p.read_text().replace(' bsr.l B8Draw',' bsr.l B8Draw\n bsr.l H5Oracle').replace(' include "RenderBitmap.s"',' include "RenderBitmap.s"\n'+asm);p.write_text(s)
# Explicit test-only workspace; far labels require long PC-relative references.
s=p.read_text()
import re
s=re.sub(r'\b(H5\w+)\(pc\)',r'(\1.l,pc)',s);p.write_text(s)
p=o/'FerrariFormulaOne/reset.py';p.write_text(p.read_text().replace(' if pc>=sy.get('," if sy.get('H5Oracle',1<<30)<=pc<sy.get('H5OraclePixels',0)+30960:continue\n if pc>=sy.get("))
out=r/'tmp/build/render-h5-oracle-owned';subprocess.run([sys.executable,str(o/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(out)],check=True)
(out/'cases.json').write_text(json.dumps(cases))

import struct
control=out.with_name(out.name+'-control');shutil.copytree(out,control,dirs_exist_ok=True);m=json.loads((out/'build.json').read_text());off=32+m['payloads']['fine']['offset']+m['payloads']['fine']['symbols']['H5OracleBenchMode'];p=control/'FerrariFormulaOne.slave';d=bytearray(p.read_bytes());assert d[off:off+2]==b'\0\1';d[off:off+2]=b'\0\0';p.write_bytes(d)
