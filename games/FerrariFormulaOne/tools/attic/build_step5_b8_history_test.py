from pathlib import Path
import struct,subprocess,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b8-history-test';o.mkdir(parents=True,exist_ok=True);base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0].replace('move.w sr','move.w ccr')
s=prefix+''' lea results(pc),a6
 lea schedule_context(pc),a0
 moveq #20,d0
 bsr.w FF1TimeInit
 clr.w $1bee8
 clr.w $1c1c2
 clr.w $1c1c4
 clr.w $1c21e
 move.w #240,$2268c
 lea $6a60a,a0
 lea $2268e,a1
 moveq #7,d0
.seed:
 move.w #3,(a0)
 move.w #10,16(a0)
 move.w #100,32(a0)
 move.w #100,96(a0)
 move.w #100,112(a0)
 clr.w (a1)+
 addq.l #2,a0
 dbra d0,.seed
 move.w #777,$6a61a
 bsr.w B8PoseTick
 bsr.w snapshot
 ; A native pulse supplies the next endpoint.
 move.w #110,$6a61c
 move.w #300,$6a62c
 move.w #200,$6a66c
 move.w #200,$6a67c
 lea events_pulse(pc),a0
 move.w #1,(a0)
 bsr.w B8PoseTick
 lea schedule_context(pc),a0
 move.w #20,FF1T_PHASE_MS(a0)
 bsr.w snapshot
 ; Explicit cut/tow invalidation must seed both endpoints from live state.
 bsr.w B8InvalidateRenderHistory
 bsr.w B8PoseTick
 bsr.w snapshot
 ; Next native pulse, then a driving-epoch change without a pulse.
 move.w #210,$6a61c
 bsr.w B8PoseTick
 lea events_pulse(pc),a0
 clr.w (a0)
 move.w #1,$1c1c2
 bsr.w B8PoseTick
 bsr.w snapshot
 ; A load reset uses the existing explicit zero-data reset spans.
 lea B8HistoryValid(pc),a0
 clr.w (a0)
 move.w #310,$6a61c
 bsr.w B8PoseTick
 bsr.w snapshot
 rts
snapshot:
 bsr.w B8PrepareRenderCopies
 lea B8RenderArena+96(pc),a0
 move.w (a0),(a6)+
 move.w 16(a0),(a6)+
 move.w 18(a0),(a6)+
 move.w 34(a0),(a6)+
 move.w 98(a0),(a6)+
 move.w 114(a0),(a6)+
 move.w $6a61c,(a6)+
 move.w $6a62c,(a6)+
 rts
 include "FerrariFormulaOne_Time.s"
 include "FerrariFormulaOne_RenderPose.s"
 include "FerrariFormulaOne_RenderHistory.s"
installed: dc.l 0
error: dc.l 0
events_pulse: dc.w 0
schedule_context: ds.b FF1T_SIZE
results: ds.b 80
'''
expected=[[3,777,10,100,100,100,10,100],[3,777,30,140,120,120,110,300],[3,777,110,300,200,200,110,300],[3,777,210,300,200,200,210,300],[3,777,310,300,200,200,310,300]]
(o/'expected.json').write_text(json.dumps(expected));(o/'history.s').write_text(s);subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_RENDER_POSES=1','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','history.list','-o','history.bin','history.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);size=len(code);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'history.bin').read_bytes();code+=b'\0'*((-len(code))%4);h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'history.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
