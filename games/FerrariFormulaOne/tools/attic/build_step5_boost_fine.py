from pathlib import Path
import struct,subprocess,hashlib,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-boost-fine';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-fuel-fine/fine.s').read_text().replace('modeval: dc.w 8','modeval: dc.w MODE')
a=asm.index('logic_tail:\n');b=asm.index(' include ',a)
asm=asm[:a]+'''logic_tail:
 movem.l d0-d7/a0-a6,-(sp)
 bsr.w boost_before
 tst.w d0
 beq.b .skip
 move.w $66faa,d0
 ext.l d0
 move.l d0,-(sp)
 jsr $6bbfc
 addq.l #4,sp
.skip:
 bsr.w boost_after
 movem.l (sp)+,d0-d7/a0-a6
 jmp $65d6e
'''+asm[b:]
body,buffers=asm.split('velocity_records: ds.b 64000',1)
extra='''boost_record:
 move.l boost_samples(pc),d0
 cmpi.l #100,d0
 bhs.w velocity_fault
 mulu.w #48,d0
 lea (boost_records.l,pc),a4
 adda.l d0,a4
 rts
boost_before:
 bsr.w boost_record
 move.l ticks(pc),(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .decided
 move.w events_pulse(pc),d0
.decided:
 move.w d0,4(a4)
 move.w $6f270,6(a4)
 move.w $1bf52,8(a4)
 move.w $66c76,10(a4)
 move.l $66c3e,12(a4)
 move.l $6bf84,20(a4)
 move.w $6bf82,28(a4)
 move.w $6f272,30(a4)
 movea.l $26600,a0
 move.l 12(a0),32(a4)
 move.l 20(a0),36(a4)
 move.w 4(a4),d0
 rts
boost_after:
 bsr.w boost_record
 move.w $66c76,16(a4)
 move.w $6bf82,18(a4)
 move.l $6bf84,24(a4)
 movea.l $26600,a0
 move.l 12(a0),40(a4)
 move.l 20(a0),44(a4)
 lea boost_samples(pc),a0
 addq.l #1,(a0)
 rts
boost_samples: dc.l 0
'''
asm=body+extra+'velocity_records: ds.b 64000'+buffers+'boost_records: ds.b 4800\n'
(o/'hooks.json').write_bytes((r/'tmp/build/step5-fuel-fine/hooks.json').read_bytes());(o/'original_div.bin').write_bytes((r/'tmp/build/step5-fuel-fine/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge'),(8,'fine')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built pulse-gated boost/audio and gear state in drawing-omission fixture')
