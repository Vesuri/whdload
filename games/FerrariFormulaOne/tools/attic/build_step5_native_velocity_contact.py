from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-native-velocity-contact';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-velocity-ownership/bridge.s').read_text().replace('modeval: dc.w 7','modeval: dc.w MODE')
asm=asm.replace('finish:\n move.w (sp)+,ccr','''finish:
 lea ticks(pc),a0
 cmpi.l #126,(a0)
 bne.b no_contact_fixture
 bsr.w contact_fixture
no_contact_fixture:
 move.w (sp)+,ccr''')
asm=asm.replace('bridge_contact_first:\n','bridge_contact_first:\n lea contact_first_count(pc),a1\n addq.l #1,(a1)\n').replace('bridge_contact_second:\n','bridge_contact_second:\n lea contact_second_count(pc),a1\n addq.l #1,(a1)\n')
cases=[dict(first=a,second=b,front=front) for a in range(7) for b in range(a+1,8) for front in (0,1)]
extra='''
contact_fixture:
 lea contact_vectors(pc),a3
 lea contact_results(pc),a4
 move.w #55,d7
case_loop:
 clr.w $1c21e
 lea velocity_shadow(pc),a0
 moveq #0,d6
seed_loop:
 move.l d6,d0
 add.l d0,d0
 lea $2268e,a1
 move.w #1,(a1,d0.l)
 lea $6a60a,a1
 move.w #10,(a1,d0.l)
 lea $6a61a,a1
 clr.w (a1,d0.l)
 lea $6a62a,a1
 move.w #100,(a1,d0.l)
 lea $2275a,a1
 move.w #100,(a1,d0.l)
 lea $6f14c,a1
 move.w #100,(a1,d0.l)
 lea $6f13c,a1
 clr.w (a1,d0.l)
 clr.w (a0)+
 move.w d6,d0
 mulu.w #257,d0
 addi.w #256,d0
 move.w d0,(a0)+
 move.w #100,(a0)+
 move.w d6,d0
 mulu.w #513,d0
 addi.w #512,d0
 move.w d0,(a0)+
 move.w d6,d0
 subq.w #4,d0
 move.w d0,(a0)+
 moveq #4,d0
 sub.w d6,d0
 move.w d0,(a0)+
 addq.w #1,d6
 cmpi.w #8,d6
 blo.w seed_loop
 moveq #0,d0
 move.w (a3)+,d0
 moveq #0,d1
 move.w (a3)+,d1
 move.w (a3)+,d2
 add.l d0,d0
 add.l d1,d1
 lea $2268e,a1
 clr.w (a1,d0.l)
 clr.w (a1,d1.l)
 tst.w d2
 bne.b second_front
 lea $6a62a,a1
 move.w #101,(a1,d0.l)
 lea $2275a,a1
 move.w #120,(a1,d1.l)
 lea $6f14c,a1
 move.w #120,(a1,d1.l)
 bra.b run_contact
second_front:
 lea $6a62a,a1
 move.w #101,(a1,d1.l)
 lea $2275a,a1
 move.w #120,(a1,d0.l)
 lea $6f14c,a1
 move.w #120,(a1,d0.l)
run_contact:
 ; Match shadow integers to the fixture input, keeping distinct tails.
 lea velocity_shadow+4(pc),a0
 lea $6f14c,a1
 moveq #7,d6
sync_seed:
 move.w (a1)+,(a0)
 adda.w #12,a0
 dbra d6,sync_seed
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68d4e
 movem.l (sp)+,d0-d7/a0-a6
 lea velocity_shadow(pc),a0
 moveq #23,d6
save_shadow:
 move.l (a0)+,(a4)+
 dbra d6,save_shadow
 lea $6a62a,a0
 moveq #3,d6
save_positions:
 move.l (a0)+,(a4)+
 dbra d6,save_positions
 lea $2275a,a0
 moveq #3,d6
save_speeds:
 move.l (a0)+,(a4)+
 dbra d6,save_speeds
 lea $6f14c,a0
 moveq #3,d6
save_velocities:
 move.l (a0)+,(a4)+
 dbra d6,save_velocities
 move.l velocity_swaps(pc),(a4)+
 dbra d7,case_loop
contact_complete:
 bra.b contact_complete
contact_first_count: dc.l 0
contact_second_count: dc.l 0
contact_vectors:
'''
for c in cases:extra+=f" dc.w {c['first']},{c['second']},{c['front']}\n"
extra+='contact_results: ds.b '+str(len(cases)*148)+'\n'
asm=asm.replace('velocity_records: ds.b 32000','')
asm+=extra+'velocity_records: ds.b 32000\n'
(o/'cases.json').write_text(json.dumps(cases,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-velocity-ownership/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built',len(cases),'native contact cases across all car pairs and both directions')
