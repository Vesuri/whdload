from pathlib import Path
import shutil,subprocess,sys,json
r=Path(__file__).resolve().parents[1];src=r/'tmp/build/render-h13-gauge-oracle-source';shutil.copytree(r/'tmp/build/render-h13-gauge-source',src,dirs_exist_ok=True)
s=(r/'tools/build_h13_oracle.py').read_text();start=s.index("asm='''")+len("asm='''");end=s.index("'''.replace('COUNT'",start);asm=s[start:end]
asm=asm.replace(' move.l $226ae,a2',' lea $1fdb8,a2').replace('#2399','#341').replace('ds.b 28800','ds.b 4104')
a=asm.index('H13OracleDraw:');b=asm.index('H13OracleSeed:',a)
asm=asm[:a]+'''
H13OracleDraw:
 move.l H13OracleCase(pc),a0
 clr.l -(sp)
 move.l #6,-(sp)
 move.l #3,-(sp)
 move.l #1,-(sp)
 move.w (a0),d0
 ext.l d0
 move.l d0,-(sp)
 move.l #12,-(sp)
 move.w 2(a0),d0
 ext.l d0
 move.l d0,-(sp)
 move.w 4(a0),d0
 ext.l d0
 move.l d0,-(sp)
 pea $1fdb8
 cmpi.w #68,(a0)
 bne.b .small
 move.l #5,-(sp)
 clr.l -(sp)
 clr.l -(sp)
 pea $255be
 bra.b .call
.small:
 move.l #3,-(sp)
 clr.l -(sp)
 clr.l -(sp)
 pea $255da
.call:
 tst.w H13OracleArm(pc)
 beq.b .native
 bsr.l H13Gauge
 bra.b .done
.native:
 jsr $24ae0
.done:
 lea 52(sp),sp
 rts
''' + asm[b:]
a=asm.index('H13OracleDispatch:');b=asm.index('H13OracleChecked:',a);asm=asm[:a]+asm[b:];asm=asm.replace('addq.l #4,(a0)','addq.l #6,(a0)')
cases=[(w,y,x) for w in (40,68) for y in (0,14,23) for x in list(range(16))+[54,68]]
asm=asm.replace('COUNT',str(len(cases)))+'\n'.join(' dc.w '+','.join(map(str,x)) for x in cases)+'\n'
p=src/'FerrariFormulaOne/Fine.s';s=p.read_text().replace('H13Control: dc.w 1','H13Control: dc.w 1\nH13GaugeCalls: dc.l 0').replace(' jsr $2a130\n move.w d1,d5',' jsr $2a130\n lea H13GaugeCalls(pc),a0\n addq.l #1,(a0)\n move.w d1,d5').replace(' bsr.l B8Draw\n',' bsr.l B8Draw\n bsr.l H13Oracle\n').replace(' include "RenderClear.s"',asm+'\n include "RenderClear.s"');p.write_text(s)
b=r/'tmp/build/render-h13-gauge-oracle';subprocess.run([sys.executable,str(src/'FerrariFormulaOne/build.py'),'--game',str(r/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'),'--out',str(b)],check=True);(b/'cases.json').write_text(json.dumps(cases))
