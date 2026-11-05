from pathlib import Path
import struct,subprocess,hashlib,json,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-recovery-separation';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-boost-fine/fine.s').read_text().replace('modeval: dc.w 8','modeval: dc.w MODE').replace(' bsr.w install_fuel\n',' bsr.w install_fuel\n bsr.w install_recovery\n',1).replace(' bsr.w boost_before\n',' bsr.w recovery_tick\n bsr.w boost_before\n',1)
body,buffers=asm.split('velocity_records: ds.b 64000',1)
hooks=[(0x6c20c,6,'player_presentation'),(0x6c5de,6,'list_clear'),(0x6c5f6,6,'opponent_presentation'),(0x682c0,6,'contact'),(0x6c6ea,6,'skip_projection'),(0x6c7c8,6,'return_before_drawing')]
existing=json.loads((r/'tmp/build/step5-boost-fine/hooks.json').read_text())
for a,n,*_ in hooks:
 for b,k,*_ in existing:assert a+n<=b or b+k<=a,(hex(a),hex(b))
for line in (r/'tmp/step4/active.dis').read_text().splitlines():
 match=re.match(r'([0-9a-f]{6}):\s+[0-9a-f]+\s+(\S+)\s+\$([0-9a-f]+)',line)
 if match and (match[2].startswith('b') or match[2] in ('jmp','jsr')):
  pc,target=int(match[1],16),int(match[3],16);assert not any(a<target<a+n and not a<=pc<a+n for a,n,*_ in hooks),line
extra="""install_recovery:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
"""
for a,n,*_ in hooks:
 for k in range(0,n,2):extra+=f' cmpi.w #${m[a+k:a+k+2].hex()},${a+k:x}\n bne.w .bad\n'
for a,n,*_ in hooks:extra+=f' lea (recovery_{a:x}.l,pc),a0\n move.w #$4ef9,${a:x}\n move.l a0,${a+2:x}\n'
extra+=""" lea recovery_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #33,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
recovery_6c20c:
 move.w sr,-(sp)
 cmpi.w #8,modeval(pc)
 beq.b .presentation
 move.w (sp)+,ccr
 move.w $2268e,d0
 jmp $6c212
.presentation:
 move.w (sp)+,ccr
 jmp $6c220
recovery_6c5de:
 move.w sr,-(sp)
 tst.w recovery_simulation(pc)
 bne.b .simulation
 move.w (sp)+,ccr
 clr.w $6a694
 jmp $6c5e4
.simulation:
 move.w (sp)+,ccr
 jmp $6c5e4
recovery_6c5f6:
 move.w sr,-(sp)
 cmpi.w #8,modeval(pc)
 bne.b .native
 tst.w recovery_simulation(pc)
 beq.b .presentation
.native:
 move.w (sp)+,ccr
 ext.l d0
 asl.l #1,d0
 movea.l d0,a0
 jmp $6c5fc
.presentation:
 move.w (sp)+,ccr
 jmp $6c6ea
recovery_6c6ea:
 move.w sr,-(sp)
 tst.w recovery_simulation(pc)
 beq.b .native
 move.w (sp)+,ccr
 jmp $6c7c0
.native:
 move.w (sp)+,ccr
 move.w -$10(a6),d0
 ext.l d0
 jmp $6c6f0
recovery_6c7c8:
 move.w sr,-(sp)
 tst.w recovery_simulation(pc)
 beq.b .native
 move.w (sp)+,ccr
 movem.l (sp)+,d2-d5
 unlk a6
 rts
.native:
 move.w (sp)+,ccr
 move.w $6a694,d0
 jmp $6c7ce
recovery_682c0:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w recovery_contact_before
 cmpi.w #8,modeval(pc)
 bne.b .run
 tst.w events_pulse(pc)
 beq.b .skip
.run:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 move.w (a0),d0
 subq.w #1,d0
 move.w d0,(a0)
 bra.b .record
.skip:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 move.w (a0),d0
.record:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w recovery_contact_after
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $682c6
recovery_contact_record:
 move.l recovery_contacts(pc),d0
 cmpi.l #800,d0
 bhs.w velocity_fault
 lsl.l #4,d0
 lea (recovery_contact_records.l,pc),a4
 adda.l d0,a4
 rts
recovery_contact_before:
 bsr.w recovery_contact_record
 move.l ticks(pc),(a4)
 move.w $32fbc,4(a4)
 move.w (a0),8(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .store
 move.w events_pulse(pc),d0
.store:
 move.w d0,6(a4)
 rts
recovery_contact_after:
 bsr.w recovery_contact_record
 move.w (a0),10(a4)
 lea recovery_contacts(pc),a1
 addq.l #1,(a1)
 rts
recovery_record:
 move.l recovery_samples(pc),d0
 cmpi.l #100,d0
 bhs.w velocity_fault
 mulu.w #256,d0
 lea (recovery_records.l,pc),a4
 adda.l d0,a4
 rts
recovery_snapshot:
 lea $2268e,a0
 moveq #7,d0
.status:
 move.w (a0)+,(a1)+
 dbra d0,.status
 lea $22356,a0
 moveq #15,d0
.fueltyre:
 move.l (a0)+,(a1)+
 dbra d0,.fueltyre
 lea $22604,a0
 moveq #7,d0
.flags:
 move.b (a0)+,(a1)+
 dbra d0,.flags
 lea fuel_remainders(pc),a0
 moveq #7,d0
.fuelcarry:
 move.w (a0)+,(a1)+
 dbra d0,.fuelcarry
 lea wear_remainders+8(pc),a0
 moveq #7,d0
.tyrecarry:
 move.w (a0)+,(a1)+
 dbra d0,.tyrecarry
 rts
recovery_tick:
 cmpi.w #7,modeval(pc)
 blo.w .done
 bsr.w recovery_record
 move.l ticks(pc),(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .pulse
 move.w events_pulse(pc),d0
.pulse:
 move.w d0,4(a4)
 move.w $1c21e,6(a4)
 move.w $66c7c,8(a4)
 move.w $66f94,10(a4)
 move.w $1c222,12(a4)
 lea 16(a4),a1
 bsr.w recovery_snapshot
 tst.w 4(a4)
 beq.b .after
 lea $2268e,a0
 moveq #1,d0
 bsr.w FF1AdvanceRecovery
 tst.w $1c21e
 bne.b .after
 lea recovery_simulation(pc),a0
 move.w #1,(a0)
 jsr $6c5c6
 lea recovery_simulation(pc),a0
 clr.w (a0)
.after:
 bsr.w recovery_record
 lea 136(a4),a1
 bsr.w recovery_snapshot
 lea recovery_samples(pc),a0
 addq.l #1,(a0)
.done:
 rts
recovery_installed: dc.l 0
recovery_contacts: dc.l 0
recovery_samples: dc.l 0
recovery_simulation: dc.w 0
"""
extra+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Logic.s')+'"\n'
asm=body+extra+'velocity_records: ds.b 64000'+buffers+'recovery_contact_records: ds.b 12800\nrecovery_records: ds.b 25600\n'
(o/'hooks.json').write_text(json.dumps(existing+hooks,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-boost-fine/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge'),(8,'fine')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built separated recovery/presentation fixture')
