#!/usr/bin/env python3
"""Local-only fixture: native mouse sampling, keyboard-consumer and quit dispatch.
Nothing is added to authoritative source or normal slave artifacts.
"""
from pathlib import Path
import os,struct,subprocess,json
root=Path(__file__).resolve().parents[1];out=root/'tmp/build/input-fixture';out.mkdir(parents=True,exist_ok=True)
for name,path in [('shipped',root/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/FerrariFormulaOne.slave'),('release',root/'tmp/build/release/FerrariFormulaOne.slave')]:
 data=bytearray(path.read_bytes());code=data[32:-4];oldsize=len(code)
 patch=code.index(bytes.fromhex('e580e580204048c1'))
 keyboard=code.index(bytes.fromhex('78004600e218'))
 asm=f'''start:
 movem.l d0-a6,-(a7)
 lea installed(pc),a0
 tst.b (a0)
 bne.w installed_done
 st (a0)
 move.w #$4eb9,$24824
 lea mouse(pc),a0
 move.l a0,$24826
 move.w #$4ef9,$236b0
 lea keyread(pc),a0
 move.l a0,$236b2
 move.w #$4eb9,$24a24
 lea buttons(pc),a0
 move.l a0,$24a26
installed_done:
 movem.l (a7)+,d0-a6
 asl.l #2,d0
 asl.l #2,d0
 move.l d0,a0
 rts
mouse:
 movem.l d1-d2/a0,-(a7)
 lea fields(pc),a0
 addq.l #1,(a0)
 move.l (a0),d1
 cmpi.l #2600,d1
 blo.b steering
 cmpi.l #2900,d1
 bhs.w nomouse
 moveq #12,d2
 sub.w $24aa8,d2
 bsr.w clamp
 move.w $24ace,d0
 add.b d2,d0
 andi.w #$ff,d0
 move.w $24aaa,d2
 subi.w #196,d2
 bsr.w clamp
 move.w $24ad0,d1
 add.b d2,d1
 lsl.w #8,d1
 or.w d1,d0
 bra.b mouseret
steering:
 cmpi.l #400,d1
 blo.b nomouse
 cmpi.l #650,d1
 bhs.b nomouse
 ; Native sampler consumes a relative delta of 8 per field; preserve Y.
 move.w $24ace,d0
 addq.b #8,d0
 andi.w #$ff,d0
 move.w $24ad0,d1
 lsl.w #8,d1
 or.w d1,d0
 bra.b mouseret
nomouse:
 move.w $dff00a,d0
mouseret:
 movem.l (a7)+,d1-d2/a0
 tst.w d0
 rts
clamp:
 cmpi.w #16,d2
 ble.b lower
 moveq #16,d2
lower:
 cmpi.w #-16,d2
 bge.b clampret
 moveq #-16,d2
clampret:
 rts
buttons:
 move.b $bfe001,d0
 movem.l d1-d2/a0,-(a7)
 lea fields(pc),a0
 move.l (a0),d1
 cmpi.l #2700,d1
 blo.b throttle
 cmpi.l #2710,d1
 bhs.b buttonret
 bclr #6,d0
 bra.b buttonret
throttle:
 cmpi.l #360,d1
 blo.b buttonret
 cmpi.l #650,d1
 bhs.b buttonret
 bclr #6,d0
buttonret:
 movem.l (a7)+,d1-d2/a0
 tst.b d0
 rts
keyread:
 movem.l d1-d2/a0-a1,-(a7)
 lea eventindex(pc),a0
 move.w (a0),d1
 mulu #6,d1
 lea events(pc),a1
 adda.l d1,a1
 move.l (a1),d1
 bmi.b nokey
 lea fields(pc),a1
 cmp.l (a1),d1
 bhi.b nokey
 move.w (a0),d1
 addq.w #1,(a0)
 mulu #6,d1
 lea events(pc),a1
 adda.l d1,a1
 move.w 4(a1),d0
 movem.l (a7)+,d1-d2/a0-a1
 cmpi.w #$59,d0
 beq.b exitkey
 move.l d0,-4(a6)
 jmp $236d8
nokey:
 movem.l (a7)+,d1-d2/a0-a1
 moveq #-1,d0
 unlk a6
 rts
exitkey:
 lea start(pc),a0
 suba.l #{oldsize},a0
 adda.l #{keyboard},a0
 moveq #$4d,d0
 jmp (a0)
installed: dc.b 0
 even
fields: dc.l 0
eventindex: dc.w 0
events:
 dc.l 200
 dc.w $40
 dc.l 300
 dc.w $45
 dc.l 350
 dc.w $45
 dc.l 700
 dc.w $27
 dc.l 6000
 dc.w $59
 dc.l -1
 dc.w 0
'''
 (out/f'{name}.s').write_text(asm)
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-Fbin','-quiet','-L',str(out/f'{name}.list'),'-o',str(out/f'{name}.bin'),str(out/f'{name}.s')],check=True)
 stub=(out/f'{name}.bin').read_bytes()
 code[patch:patch+6]=bytes.fromhex('6100')+struct.pack('>h',oldsize-patch-2)+bytes.fromhex('4e71')
 code+=stub;code+=b'\0'*((-len(code))%4)
 data[20:24]=struct.pack('>I',len(code)//4);data[28:32]=data[20:24]
 (out/f'{name}.slave').write_bytes(data[:32]+code+bytes.fromhex('000003f2'))
 print(name,'fixture bytes',len(stub),'original patch offset',hex(patch),'keyboard offset',hex(keyboard))
