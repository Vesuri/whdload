from pathlib import Path
import shutil,subprocess,sys
r=Path(__file__).resolve().parents[1];src=r/'tmp/build/render-h10-bench-source';shutil.copytree(r/'tmp/build/render-h9-grid-source',src,dirs_exist_ok=True)
f=src/'Fine.s'
print(list(src.glob('*Fine*')))
f=src/'FerrariFormulaOne/Fine.s';s=f.read_text().replace(' bsr.l FF1RenderInstallFill',' bsr.l H10BenchInstall\n bsr.l FF1RenderInstallFill');extra='''
H10BenchInstall:
 tst.w H10BenchControl(pc)
 beq.b .done
 lea H10BenchBottom(pc),a0
 move.w #$4eb9,$6b0e4
 move.l a0,$6b0e6
 lea H10BenchTop(pc),a0
 move.w #$4eb9,$6b138
 move.l a0,$6b13a
 move.w #$4e71,$6b13e
.done:
 rts
H10BenchBottom:
 movem.l d0-d7/a0-a5,-(sp)
 move.w d0,d7
 lsr.w #6,d7
 moveq #0,d0
 cmpi.w #2,-2(a6)
 bne.b H10BenchFill
 moveq #-1,d0
 bra.b H10BenchFill
H10BenchTop:
 movem.l d0-d7/a0-a5,-(sp)
 moveq #17,d7
 moveq #0,d0
 tst.w -2(a6)
 bne.b H10BenchFill
 moveq #-1,d0
H10BenchFill:
 move.l a1,a5
 move.l d0,d1
 move.l d0,d2
 move.l d0,d3
 move.l d0,d4
 move.l d0,d5
 move.l d0,d6
 move.l d0,a0
 move.l d0,a1
 move.l d0,a2
 move.l d0,a3
 move.l d0,a4
 subq.w #1,d7
.loop:
 movem.l d0-d6/a0-a4,(a5)
 lea 48(a5),a5
 dbra d7,.loop
 movem.l (sp)+,d0-d7/a0-a5
 rts
H10BenchControl: dc.w 1
''';s=s.replace(' include "RenderFill.s"',extra+'\n include "RenderFill.s"');f.write_text(s)
o=r/'tmp/build/render-h10-bench';subprocess.run([sys.executable,str(src/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(o)],check=True)
import json
c=o.with_name(o.name+'-control');shutil.copytree(o,c,dirs_exist_ok=True);m=json.loads((o/'build.json').read_text());at=32+m['payloads']['fine']['offset']+m['payloads']['fine']['symbols']['H10BenchControl'];p=c/'FerrariFormulaOne.slave';b=bytearray(p.read_bytes());assert b[at:at+2]==b'\0\1';b[at:at+2]=b'\0\0';p.write_bytes(b)
