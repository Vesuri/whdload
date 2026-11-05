from pathlib import Path
import struct,subprocess,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-elapsed';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes()
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-recovery-separation/fine.s').read_text()
asm=asm.replace(' move.l #$65174,$65f30',' lea (schedule_end.l,pc),a1\n move.l a1,$65f30',1)
asm=asm.replace(' bsr.w install_recovery\n',' bsr.w install_recovery\n bsr.w schedule_install\n',1)
asm=asm.replace('finish:\n bsr.w events_quantum','finish:\n bsr.w schedule_begin',1)
body,buffers=asm.split('velocity_records: ds.b 64000',1)
extra='''
schedule_install:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.l #$33c10002,$24946
 bne.w schedule_bad
 cmpi.w #$4ad2,$2494a
 bne.w schedule_bad
 lea (schedule_context.l,pc),a0
 moveq #20,d0
 bsr.w FF1TimeInit
 move.l $4.w,a6
 jsr -120(a6)
 lea (schedule_vbl.l,pc),a0
 move.w #$4eb9,$24946
 move.l a0,$24948
 lea (start.l,pc),a2
 suba.l #5440,a2
 move.l $1180(a2),a2
 jsr $20(a2)
 move.l $4.w,a6
 jsr -126(a6)
 movem.l (sp)+,d0-d7/a0-a6
 rts
schedule_bad:
 lea error(pc),a0
 move.l #35,(a0)
 bra.w velocity_fault
schedule_vbl:
 move.w d1,$24ad2
 movem.l d0-d3/a0-a1,-(sp)
 move.w sr,-(sp)
 lea (schedule_context.l,pc),a0
 bsr.w FF1TimeField
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d3/a0-a1
 rts
schedule_record:
 move.l schedule_completed(pc),d0
 cmpi.l #100,d0
 bhs.w schedule_stop
 mulu.w #32,d0
 lea (schedule_records.l,pc),a4
 adda.l d0,a4
 rts
schedule_begin:
 cmpi.l #126,ticks(pc)
 blo.w .done
 lea (schedule_context.l,pc),a0
.wait:
 bsr.w FF1TimeDue
 tst.l d0
 beq.b .wait
 bsr.w schedule_record
 move.l FF1T_FIELDS(a0),(a4)
 move.l d2,8(a4)
 move.l d1,12(a4)
 move.l ticks(pc),24(a4)
 ; Preview this tick's native pulse. Only schedule_end commits elapsed time.
 move.w FF1T_PHASE_MS(a0),d0
 addi.w #20,d0
 lea events_pulse(pc),a1
 clr.w (a1)
 cmpi.w #100,d0
 blo.b .done
 move.w #1,(a1)
 lea events_pulses(pc),a1
 addq.l #1,(a1)
.done:
 rts
schedule_end:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w schedule_record
 lea (schedule_context.l,pc),a0
 move.l FF1T_FIELDS(a0),4(a4)
 bsr.w FF1TimeConsume
 move.l d0,28(a4)
 cmp.w events_pulse(pc),d0
 bne.w schedule_bad
 bsr.w FF1TimeDue
 move.l d2,16(a4)
 move.l d1,20(a4)
 lea schedule_completed(pc),a1
 addq.l #1,(a1)
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $65174
schedule_stop:
 bra.b schedule_stop
schedule_completed: dc.l 0
 include "TIMECORE"
schedule_context: ds.b FF1T_SIZE
'''.replace('TIMECORE',str(r.parent.parent/'Games/FerrariFormulaOne_Time.s'))
asm=body+extra+'velocity_records: ds.b 64000'+buffers+'schedule_records: ds.b 3200\n'
(o/'fine.s').write_text(asm);(o/'original_div.bin').write_bytes((r/'tmp/build/step5-recovery-separation/original_div.bin').read_bytes())
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built elapsed-time combined logic diagnostic')
