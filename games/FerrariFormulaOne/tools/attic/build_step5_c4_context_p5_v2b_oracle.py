from pathlib import Path
import struct,subprocess,json,os
r=Path(__file__).resolve().parents[1];mode=int(os.environ.get('P5_CONTEXT_MODE','0'));o=r/f'tmp/build/step5-c4-context-p5-v2b-oracle-{mode}';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];size=len(normal)
cases=[(kind,index,ccr, (index*12 if kind==0 else 0) if index<8 else 0xffffffff, (ccr&16)|(4 if kind or index==0 else 0) if index<8 else (ccr&16)|8) for kind in range(2) for index in (range(8) if kind==0 else [*range(8),8,255,65535]) for ccr in range(32)]
(o/'cases.bin').write_bytes(b''.join(struct.pack('>HHHII',*x) for x in cases))
m=(r.parents[1]/'Games/FerrariFormulaOne_Coarse200Motion.s').read_text();helper=m[m.index('velocity_context:'):m.index('velocity_sync:')]+m[m.index('bridge_context:'):m.index('bridge_load:')]
# Keep the helper instructions intact; native $32fbc is valid in this release
# fixture. Preserve its original value around the exhaustive valid-index tests.
if mode==1:helper=helper.replace(' move.l d0,a0\n adda.w d0,a0\n move.w .p5_offsets(pc,a0.w),d0',' mulu.w #12,d0\n nop\n nop')
start=(r/'tmp/build/step5-c3-track-test/track.s').read_text().split('tests:')[0]
s=start+'''tests:
 move.w $32fbc,-(sp)
 lea cases(pc),a2
 move.w #COUNT-1,d7
.loop:
 move.w 2(a2),$32fbc
 lea velocity_context(pc),a4
 tst.w (a2)
 beq.b .selected
 lea bridge_context(pc),a4
.selected:
 lea snapshots(pc),a3
 move.l #$11112222,d1
 move.l #$22223333,d2
 move.l #$33334444,d3
 move.l #$44445555,d4
 move.l #$55556666,d5
 move.l #$66667777,d6
 movea.l #$12345678,a1
 movea.l #$23456789,a6
 move.l sp,a5
 movem.l d1-d7/a1-a6,(a3)
 move.l #$abcdef98,d0
 move.w 4(a2),ccr
 jsr (a4)
 move.w sr,-(sp)
 movem.l d1-d7/a1-a6,52(a3)
 cmp.l 6(a2),d0
 bne.w .bad_pop
 move.w (sp)+,d1
 andi.l #31,d1
 cmp.l 10(a2),d1
 bne.w .bad
 cmpa.l sp,a5
 bne.w .bad
 move.l a0,d0
 lea velocity_shadow(pc),a0
 tst.w (a2)
 beq.b .pointer
 lea position_shadow(pc),a0
 cmpi.w #7,2(a2)
 bls.b .pointer
 lea error(pc),a0
 bra.b .compare_pointer
.pointer:
 moveq #0,d1
 move.w 2(a2),d1
 mulu.w #12,d1
 adda.l d1,a0
.compare_pointer:
 cmpa.l d0,a0
 bne.b .bad
 move.l a3,a0
 lea 52(a3),a1
 moveq #12,d0
.regs:
 cmpm.l (a0)+,(a1)+
 bne.b .bad
 dbra d0,.regs
 lea error(pc),a0
 clr.l (a0)
 lea checked(pc),a0
 addq.l #1,(a0)
 adda.w #14,a2
 dbra d7,.loop
 move.w (sp)+,$32fbc
 rts
.bad_pop:
 addq.l #2,sp
.bad:
 lea error(pc),a0
 move.l #1,(a0)
 move.w (sp)+,$32fbc
 rts
'''.replace('COUNT',str(len(cases)))+helper+'''
velocity_fault:
 lea error(pc),a0
 move.l #17,(a0)
 rts
installed: dc.l 0
checked: dc.l 0
error: dc.l 0
snapshots: ds.l 26
velocity_shadow: ds.b 96
position_shadow: ds.b 96
cases: incbin "cases.bin"
'''
(o/'wide.s').write_text(s)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-DFF1_C4_CONTEXT_P5=1','-Fbin','-quiet','-L','wide.list','-o','wide.bin','wide.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'wide.bin').read_bytes();code+=b'\0'*((-len(code))%4)
h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'wide.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
(o/'expected.json').write_text(json.dumps({'comparisons':len(cases),'mode':mode,'scope':'All eight indices and all 32 CCR values, D0/A0 result, D1-D7/A1-A7 preservation; three invalid position indices.'})+'\n')
t=(r/'tools/test_step5_c4_wide.py').read_text().replace('step5-c4-wide',f'step5-c4-context-p5-v2b-oracle-{mode}').replace('c4-wide-oracle',f'c4-context-p5-v2b-oracle-{mode}').replace('FerrariFormulaOne_Wide000.s','FerrariFormulaOne_Coarse200Motion.s');(r/'tools/test_step5_c4_context_p5_v2b_oracle.py').write_text(t)
print('Built',len(cases),'context cases',mode)
