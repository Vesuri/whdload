from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-native-velocity-working';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-velocity-ownership-v2/bridge.s').read_text().replace('modeval: dc.w 7','modeval: dc.w MODE').replace('velocity_records: ds.b 32000','')
asm=asm.replace('finish:\n move.w (sp)+,ccr','''finish:
 lea ticks(pc),a0
 cmpi.l #126,(a0)
 bne.b no_writer_fixture
 bsr.w writer_fixture
no_writer_fixture:
 move.w (sp)+,ccr''')
extra='''writer_fixture:
 lea writer_return(pc),a0
'''
for dest in (0x6838c,0x6e2aa,0x6e2f2,0x69b3c,0x69b56,0x6ee06,0x6ee1e):
 extra+=f''' move.w #$4ef9,${dest:x}
 move.l a0,${dest+2:x}
'''
extra+=''' lea start(pc),a2
 suba.l #5440,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 lea fake_frame+16(pc),a6
 lea writer_results(pc),a4
 moveq #0,d7
writer_case:
'''
ops=[('zero_a',0x68380,0),('zero_b',0x6e29e,0),('projection',0x6e2ec,23),('clamp10',0x69b36,10),('clamp100',0x69b50,100),('impulse_a',0x6ee00,7),('impulse_b',0x6ee16,-9)]
for name,entry,value in ops:
 extra+=f""" bsr.w writer_seed
 move.w d7,$32fbc
 clr.w $32f94
 move.w #200,$32f96
 move.l d7,d5
 add.l d5,d5
 lea $6f13c,a0
 adda.l d5,a0
 moveq #0,d0
 moveq #0,d1
"""
 if name=='projection':extra+=' move.w #17,$32f94\n'
 if name.startswith('impulse'):extra+=f' move.w #{value},d1\n'
 else:extra+=f' move.w #{value},d0\n'
 extra+=f""" movem.l d0-d7/a0-a6,-(sp)
 jsr ${entry:x}
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
"""
extra+=''' addq.w #1,d7
 cmpi.w #8,d7
 blo.w writer_case
writer_complete:
 bra.b writer_complete
writer_return:
 rts
writer_seed:
 lea velocity_shadow(pc),a0
 lea $6f13c,a1
 lea $6f14c,a2
 moveq #0,d6
.loop:
 clr.w (a1)+
 move.w #200,(a2)+
 move.l d6,d0
 mulu.w #257,d0
 addi.l #256,d0
 move.l d0,(a0)+
 move.l d6,d0
 mulu.w #513,d0
 addi.l #$00c80200,d0
 move.l d0,(a0)+
 move.w d6,d0
 subq.w #4,d0
 move.w d0,(a0)+
 moveq #4,d0
 sub.w d6,d0
 move.w d0,(a0)+
 addq.w #1,d6
 cmpi.w #8,d6
 blo.b .loop
 rts
writer_save:
 lea velocity_shadow(pc),a0
 moveq #23,d6
.shadow:
 move.l (a0)+,(a4)+
 dbra d6,.shadow
 lea $6f13c,a0
 moveq #7,d6
.arrays:
 move.l (a0)+,(a4)+
 dbra d6,.arrays
 move.l $32f94,(a4)+
 move.l velocity_work_resets(pc),(a4)+
 move.l velocity_clamps(pc),(a4)+
 move.l velocity_impulses(pc),(a4)+
 rts
fake_frame: ds.b 64
writer_results: ds.b 8064
'''
asm+=extra+'''velocity_records: ds.b 32000
'''
(o/'original_div.bin').write_bytes((r/'tmp/build/step5-velocity-ownership-v2/original_div.bin').read_bytes())
(o/'cases.json').write_text(json.dumps([dict(car=car,operation=op) for car in range(8) for op,_,_ in ops],indent=2)+'''
''')
for mode,name in ((6,'control'),(7,'bridge')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built 56 seeded native velocity instruction-group cases')
