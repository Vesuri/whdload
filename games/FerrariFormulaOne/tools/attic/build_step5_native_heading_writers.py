from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-native-heading-writers';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-heading-fine/heading.s').read_text().replace('modeval: dc.w 9','modeval: dc.w MODE').replace('fine_records: ds.b 25600','').replace('heading_records: ds.b 38400','')
asm=asm.replace('finish:\n move.w (sp)+,ccr','''finish:
 lea ticks(pc),a0
 cmpi.l #126,(a0)
 bne.b no_writer_fixture
 bsr.w writer_fixture
no_writer_fixture:
 move.w (sp)+,ccr''')
extra='writer_fixture:\n lea writer_return(pc),a0\n'
for dest in (0x6732c,0x683b8,0x68a64,0x68c2e,0x68d16):
 extra+=f' move.w #$4ef9,${dest:x}\n move.l a0,${dest+2:x}\n'
extra+=''' lea start(pc),a2
 suba.l #5440,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 lea fake_frame+16(pc),a6
 lea writer_results(pc),a4
 moveq #0,d7
writer_case:
'''
ops=[('zero_a',0x67320),('zero_b',0x683ac),('cold_zero_a',0x68a5e),('cold_zero_b',0x68c24),('assign_world',0x68d0e)]
for name,entry in ops:
 extra+=f''' bsr.w writer_seed
 movem.l d0-d7/a0-a6,-(sp)
 jsr ${entry:x}
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
'''
extra+=''' addq.w #1,d7
 cmpi.w #8,d7
 blo.w writer_case
writer_complete:
 bra.b writer_complete
writer_return:
 rts
writer_seed:
 lea heading_shadow(pc),a0
 lea $2278a,a1
 lea $227aa,a2
 moveq #0,d6
.loop:
 move.l d6,d0
 mulu.w #12345,d0
 subi.l #50000,d0
 move.l d0,(a1)+
 move.l d0,(a0)+
 move.w d6,d0
 subq.w #4,d0
 move.w d0,(a0)+
 move.l d6,d0
 mulu.w #45678,d0
 addi.l #90000,d0
 move.l d0,(a2)+
 move.l d0,(a0)+
 moveq #4,d0
 sub.w d6,d0
 move.w d0,(a0)+
 addq.w #1,d6
 cmpi.w #8,d6
 blo.b .loop
 move.w d7,$32fbc
 move.l d7,d5
 lsl.l #2,d5
 lea $2278a,a0
 adda.l d5,a0
 move.l (a0),$32fb4
 lea $227aa,a1
 adda.l d5,a1
 move.l (a1),$32fb8
 move.l #$12345000,-10(a6)
 move.l $32fb4,d0
 move.l d0,d1
 rts
writer_save:
 lea heading_shadow(pc),a0
 moveq #23,d6
.shadow:
 move.l (a0)+,(a4)+
 dbra d6,.shadow
 lea $2278a,a0
 moveq #15,d6
.arrays:
 move.l (a0)+,(a4)+
 dbra d6,.arrays
 move.l $32fb4,(a4)+
 move.l $32fb8,(a4)+
 rts
fake_frame: ds.b 32
writer_results: ds.b 6720
'''
# The world assignment uses A0=world destination and A1=relative source.
extra=extra.replace(' bsr.w writer_seed\n movem.l d0-d7/a0-a6,-(sp)\n jsr $68d0e', ' bsr.w writer_seed\n exg a0,a1\n movem.l d0-d7/a0-a6,-(sp)\n jsr $68d0e')
asm+=extra+'fine_records: ds.b 25600\nheading_records: ds.b 38400\n'
(o/'original_div.bin').write_bytes((r/'tmp/build/step5-heading-fine/original_div.bin').read_bytes())
(o/'cases.json').write_text(json.dumps([dict(car=car,operation=op) for car in range(8) for op,_ in ops],indent=2)+'\n')
for mode,name in ((6,'control'),(9,'heading')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built 40 seeded native heading instruction-group cases')
