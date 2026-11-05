from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-native-position-writers';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-position-bridge-v3/bridge.s').read_text().replace('modeval: dc.w 7','modeval: dc.w MODE')
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
# Return after each native instruction group; no full modal transition claimed.
for dest in (0x663fa,0x68c18,0x6895e,0x688e8,0x68920,0x68ac0,0x68b2c):
 extra+=f' move.w #$4ef9,${dest:x}\n move.l a0,${dest+2:x}\n'
extra+=''' lea start(pc),a2
 suba.l #5440,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 lea fake_frame+16(pc),a6
 lea writer_results(pc),a4
 moveq #0,d7
writer_case:
 lea position_shadow(pc),a0
 lea saved_position(pc),a1
 moveq #0,d6
writer_seed:
 move.w d6,d0
 mulu.w #12,d0
 move.l d6,d1
 add.l d1,d1
 lea $6a61a,a2
 move.w #10,(a2,d1.l)
 lea $6a62a,a2
 move.w #100,(a2,d1.l)
 lea $227ca,a2
 move.w #50,(a2,d1.l)
 move.w #10,(a0)+
 move.w d6,d0
 mulu.w #257,d0
 addi.w #256,d0
 move.w d0,(a0)+
 move.w d6,d0
 subq.w #4,d0
 move.w d0,(a0)+
 move.w #100,(a0)+
 move.w d6,d0
 mulu.w #513,d0
 addi.w #512,d0
 move.w d0,(a0)+
 move.w d6,d0
 subq.w #4,d0
 move.w d0,(a0)+
 move.w #50,(a1)+
 move.l #$12340002,(a1)+
 addq.w #1,d6
 cmpi.w #8,d6
 blo.b writer_seed
 move.l d7,d5
 add.l d5,d5
 lea $227ca,a0
 adda.l d5,a0
 lea $6a62a,a1
 adda.l d5,a1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $663f4
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
 ; Change the current coordinate and tail after snapshot, before restore.
 move.l d7,d0
 mulu.w #12,d0
 lea position_shadow+6(pc),a0
 adda.l d0,a0
 move.w #200,(a0)
 move.l #$beef0003,2(a0)
 lea $6a62a,a0
 adda.l d5,a0
 move.w #200,(a0)
 lea $227ca,a1
 adda.l d5,a1
 movem.l d0-d7/a0-a6,-(sp)
 jsr $68c12
 movem.l (sp)+,d0-d7/a0-a6
 bsr.w writer_save
'''
ops=[(0x6886e,0x6a61a,111,'d1'),(0x688e2,0x6a62a,222,'d0'),(0x68918,0x6a61a,333,'d0'),(0x68ab8,0x6a61a,444,'d0'),(0x68b26,0x6a62a,0,'d0')]
for entry,array,value,reg in ops:
 # Reseed the target tail even when its integer matches a previous write.
 offset=0 if array==0x6a61a else 6
 extra+=f''' move.l d7,d0
 mulu.w #12,d0
 lea position_shadow+{offset}(pc),a0
 adda.l d0,a0
 move.l #$f00dfffd,2(a0)
 lea ${array:x},a0
 adda.l d5,a0
 move.w #{value},{reg}
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
writer_save:
 lea position_shadow(pc),a0
 moveq #23,d6
.shadow:
 move.l (a0)+,(a4)+
 dbra d6,.shadow
 lea saved_position(pc),a0
 moveq #11,d6
.saved:
 move.l (a0)+,(a4)+
 dbra d6,.saved
 lea $6a61a,a0
 moveq #7,d6
.arrays:
 move.l (a0)+,(a4)+
 dbra d6,.arrays
 lea $227ca,a0
 moveq #3,d6
.native_saved:
 move.l (a0)+,(a4)+
 dbra d6,.native_saved
 rts
fake_frame: ds.b 32
writer_results: ds.b 10752
'''
asm+=extra
(o/'original_div.bin').write_bytes((r/'tmp/build/step5-position-bridge-v3/original_div.bin').read_bytes())
(o/'cases.json').write_text(json.dumps([dict(car=car,operation=op) for car in range(8) for op in ('snapshot','restore','init_x_111','init_z_222','init_x_333','init_x_444','zero_z')],indent=2)+'\n')
for mode,name in ((6,'control'),(7,'bridge')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built 56 native writer instruction-group cases')
