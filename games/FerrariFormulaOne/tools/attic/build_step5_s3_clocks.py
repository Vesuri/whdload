from pathlib import Path
import json,struct,re,subprocess,calendar
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-s3-clocks';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
s=(r/'tmp/build/step5-s3/verify-p0/fine.s').read_text().replace(' bsr.w FF1InstallPresentation\n',' bsr.w FF1InstallPresentation\n bsr.w clock_tests\n bra.l clock_test_stop\n')
cases=[]
seeds=[(24,1,15,12,34,56,0),(24,1,15,12,34,56,9),(24,1,15,12,34,59,9),(24,1,15,12,59,59,9),(24,1,15,19,59,59,9),(24,1,15,23,59,59,9),(24,2,28,23,59,59,9),(24,2,29,23,59,59,9),(23,2,28,23,59,59,9),(24,4,30,23,59,59,9),(99,12,31,23,59,59,9)]
def pack(y,m,d,h,mi,sec,t):return bytes([y,m,d,h//10,h%10,mi//10,mi%10,sec//10,sec%10,t])
for seed in seeds:
 for which in (0,1):
  for display in (0,1):
   for pulse in (0,1):
    for passes in (0,1,3):
     y,m,d,h,mi,sec,t=seed
     if pulse:
      t+=1
      if t==10:
       t=0;sec+=1
       if sec==60:
        sec=0;mi+=1
        if mi==60:
         mi=0;h+=1
         if h==24:
          h=0;d+=1
          if d>calendar.monthrange(2000+y,m)[1]:
           d=1;m+=1
           if m==13:m=1;y=(y+1)%100
     before=pack(*seed);after=pack(y,m,d,h,mi,sec,t)
     cases.append(dict(which=which,display=display,pulse=pulse,passes=passes,seed=list(seed),input_hex=(struct.pack('>4H',which,display,pulse,passes)+before).hex(),expected_hex=(after+before if which==0 else before+after).hex()))
extra='''
clock_tests:
 ; Isolated calendar drawing reuses the live race planes. Its fourth plane
 ; aliases the first: this tests real DMA/state independence, not menu pixels.
 lea clock_menu_planes(pc),a0
 move.l $226ae,a1
 move.l (a1),(a0)+
 move.l 4(a1),(a0)+
 move.l 8(a1),(a0)+
 move.l (a1),(a0)
 ; Calendar's native month helper may replace the race overlay. Keep both
 ; race plane lists outside that overlay for subsequent isolated glyph calls.
 lea clock_race_planes(pc),a0
 move.l $226ae,a1
 move.l (a1)+,(a0)+
 move.l (a1)+,(a0)+
 move.l (a1)+,(a0)+
 move.l $226b2,a1
 move.l (a1)+,(a0)+
 move.l (a1)+,(a0)+
 move.l (a1)+,(a0)+
 lea clock_race_planes(pc),a0
 move.l a0,$226ae
 lea 12(a0),a0
 move.l a0,$226b2
 lea clock_menu_planes-8(pc),a0
 lea clock_menu_bitmap(pc),a1
 move.l a0,4(a1)
 move.l a1,$243cc
 cmpi.l #$4e560000,$23946
 bne.w clock_test_bad
 cmpi.l #$48e72000,$2394a
 bne.w clock_test_bad
 lea clock_glyph(pc),a0
 move.l a0,$23948
 move.w #$4ef9,$23946
 move.w #$4e71,$2394c
 lea start(pc),a2
 suba.l #5440,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 lea clock_test_index(pc),a0
 clr.l (a0)
.next:
 move.l clock_test_index(pc),d0
 cmpi.l #COUNT,d0
 bhs.w .done
 mulu.w #18,d0
 lea (clock_test_inputs.l,pc),a5
 adda.l d0,a5
 lea 8(a5),a0
 lea $226c0,a1
 lea $226ca,a2
 moveq #9,d0
.seed:
 move.b (a0)+,d1
 move.b d1,(a1)+
 move.b d1,(a2)+
 dbra d0,.seed
 move.w 2(a5),$1c1e8
 ; Compare native arithmetic with drawing against the split, from the same seed.
 lea $226c0,a4
 tst.w (a5)
 beq.b .pointer
 lea $226ca,a4
.pointer:
 tst.w 4(a5)
 beq.b .reference
 movem.l a4-a5,-(sp)
 move.l a4,-(sp)
 jsr $22c3a
 addq.l #4,sp
 movem.l (sp)+,a4-a5
.reference:
 lea $226c0,a0
 lea clock_reference(pc),a1
 moveq #19,d0
.copyref:
 move.b (a0)+,(a1)+
 dbra d0,.copyref
 lea 8(a5),a0
 lea $226c0,a1
 lea $226ca,a2
 moveq #9,d0
.reset:
 move.b (a0)+,d1
 move.b d1,(a1)+
 move.b d1,(a2)+
 dbra d0,.reset
 tst.w 4(a5)
 beq.b .present
 movem.l a4-a5,-(sp)
 move.l a4,-(sp)
 bsr.w FF1ClockTick
 addq.l #4,sp
 movem.l (sp)+,a4-a5
.present:
 lea clock_glyph_calls(pc),a0
 clr.l (a0)
 move.w 6(a5),d7
 beq.b .record
.draw:
 bsr.w FF1PresentClock
 subq.w #1,d7
 bne.b .draw
.record:
 move.l clock_test_index(pc),d0
 mulu.w #48,d0
 lea (clock_test_results.l,pc),a1
 adda.l d0,a1
 lea $226c0,a0
 moveq #19,d0
.copy:
 move.b (a0)+,(a1)+
 dbra d0,.copy
 lea clock_reference(pc),a0
 moveq #19,d0
.ref:
 move.b (a0)+,(a1)+
 dbra d0,.ref
 move.l error(pc),(a1)+
 move.l clock_glyph_calls(pc),(a1)+
 lea clock_test_index(pc),a0
 addq.l #1,(a0)
 bra.w .next
.done:
 lea clock_test_complete(pc),a0
 move.l #1,(a0)
 rts
clock_test_bad:
 lea error(pc),a0
 move.l #38,(a0)
 rts
clock_glyph:
 link a6,#0
 movem.l d2,-(sp)
 move.w ccr,-(sp)
 move.l a0,-(sp)
 lea clock_glyph_calls(pc),a0
 addq.l #1,(a0)
 move.l (sp)+,a0
 move.w (sp)+,ccr
 jmp $2394e
clock_glyph_calls: dc.l 0
clock_test_stop: bra.b clock_test_stop
clock_test_index: dc.l 0
clock_test_complete: dc.l 0
clock_reference: ds.b 20
clock_menu_bitmap: ds.l 8
clock_menu_planes: ds.l 4
clock_race_planes: ds.l 6
clock_test_inputs:
'''.replace('COUNT',str(len(cases)))
extra+=''.join(' dc.b '+','.join('$'+c['input_hex'][i:i+2] for i in range(0,36,2))+'\n' for c in cases)
extra+=f'clock_test_results: ds.b {len(cases)*48}\n'
s=s.replace(' FF1UpdateWorkspace',extra+' FF1UpdateWorkspace')
s=s.replace(' include "FerrariFormulaOne_UpdateHooks.s"',(r.parents[1]/'Games/FerrariFormulaOne_UpdateHooks.s').read_text())
# No motion or event callbacks execute in this isolated fixture.
s=re.sub(r'^(\w+): ds\.[bl] (\d+)$',lambda m:m[1]+': ds.b 4' if ('records' in m[1] or m[1] in ('velocity_target_speeds','position_velocity_inputs')) else m[0],s,flags=re.M)
(o/'fine.s').write_text(s);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-s3/verify-p0/original_div.bin').read_bytes())
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-DVERIFY=1','-DFF1_PRESENTATION_SPLIT=1','-DFF1_PRESENTATION_CALLBACK=1','-I'+str(r.parents[1]/'Games'),'-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);size=len(code);listing=(o/'fine.list').read_text();entry=int(re.search(r'^selection_boot\s+00:([0-9A-F]+)',listing,re.M)[1],16);assert size+entry<32768;struct.pack_into('>H',code,24,size+entry)
pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
h=bytearray(base[:32]);struct.pack_into('>I',h,20,len(code)//4);h[28:32]=h[20:24];(o/'fine.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
print(len(cases),'clock carry/presentation cases')
