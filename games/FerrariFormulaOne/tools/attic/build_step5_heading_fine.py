from pathlib import Path
import struct,subprocess,hashlib,json,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-heading-fine';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-position-fine/fine.s').read_text().replace('modeval: dc.w 8','modeval: dc.w MODE').replace(' bsr.w install_fine_position\n',' bsr.w install_fine_position\n bsr.w install_heading\n').replace(' cmpi.w #8,d0\n bne.w .done',' cmpi.w #8,d0\n blo.w .done').replace('fine_records: ds.b 25600','')
m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
hooks=[(0x67280,6,'sync',True),(0x6860e,6,'sync',True),(0x678de,6,'step_a',False),(0x67900,6,'step_b',False),(0x67948,6,'step_a',False),(0x67976,6,'step_b',False),(0x67320,12,'zero',False),(0x683ac,12,'zero',False),(0x69590,6,'reset_a',True),(0x695e8,6,'reset_b',True),(0x68a5e,6,'reset_a',True),(0x68c24,10,'reset_a',True),(0x68d0e,8,'assign_b',True)]
for line in (r/'tmp/step4/active.dis').read_text().splitlines():
 match=re.match(r'([0-9a-f]{6}):\s+[0-9a-f]+\s+(\S+)\s+\$([0-9a-f]+)',line)
 if not match or not (match[2].startswith('b') or match[2] in ('jmp','jsr')):continue
 pc,target=int(match[1],16),int(match[3],16)
 assert not any(a<target<a+n and not a<=pc<a+n for a,n,*_ in hooks),line
extra='''install_heading:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #9,d0
 bne.w .done
'''
for a,n,kind,displaced in hooks:
 for k in range(0,n,2):extra+=f' cmpi.w #${m[a+k:a+k+2].hex()},${a+k:x}\n bne.w .bad\n'
for a,n,kind,displaced in hooks:
 extra+=f' lea heading_{a:x}(pc),a0\n move.w #$4ef9,${a:x}\n move.l a0,${a+2:x}\n'
 for k in range(6,n,2):extra+=f' move.w #$4e71,${a+k:x}\n'
extra+=''' lea heading_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #15,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
'''
for a,n,kind,displaced in hooks:
 extra+=f'heading_{a:x}:\n'
 if displaced:extra+=' dc.w '+','.join('$'+m[a+k:a+k+2].hex() for k in range(0,n,2))+'\n'
 extra+=' movem.l d0-d7/a0-a6,-(sp)\n move.w sr,-(sp)\n move.l d0,d4\n'
 # All inspected sites execute in loops whose $32fbc is this car.
 extra+=' bsr.w heading_context\n'
 extra+=f' bsr.w heading_{kind}\n move.w (sp)+,ccr\n movem.l (sp)+,d0-d7/a0-a6\n jmp ${a+n:x}\n'
extra+='''heading_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 bhi.w fine_fault
 mulu.w #12,d0
 lea heading_shadow(pc),a0
 adda.l d0,a0
 rts
heading_sync:
 move.l $32fb4,(a0)
 move.l $32fb8,6(a0)
 rts
heading_step_a:
 moveq #0,d5
 bra.b heading_step
heading_step_b:
 moveq #1,d5
 addq.l #6,a0
heading_step:
 move.l a0,a3
 move.l heading_steps(pc),d0
 cmpi.l #1600,d0
 bhs.w fine_fault
 mulu.w #24,d0
 lea heading_records(pc),a4
 adda.l d0,a4
 move.w $32fbc,(a4)
 move.w d5,2(a4)
 move.l d4,4(a4)
 lea $32fb4,a2
 tst.w d5
 beq.b .axis_ready
 addq.l #4,a2
.axis_ready:
 move.l (a2),(a0)
 move.l (a0),8(a4)
 move.w 4(a0),12(a4)
 clr.w 14(a4)
 move.l d4,d0
 bsr.w FF1Heading20
 tst.l d1
 bne.w fine_fault
 move.l (a0),(a2)
 move.l (a0),16(a4)
 move.w 4(a0),20(a4)
 move.w d1,22(a4)
 lea heading_steps(pc),a1
 addq.l #1,(a1)
 rts
heading_zero:
 bsr.w heading_sync
 bsr.w FF1HeadingZeroRelative
 move.l (a0),$32fb4
 move.l 6(a0),$32fb8
 lea heading_zeroes(pc),a1
 addq.l #1,(a1)
 rts
heading_reset_a:
 ; Cold array resets write zero; recovery writes -4<<16. Read the authoritative
 ; per-car relative array rather than stale shared scratch on cold paths.
 moveq #0,d0
 move.w $32fbc,d0
 lsl.l #2,d0
 lea $2278a,a1
 move.l (a1,d0.l),d0
 bsr.w FF1HeadingReset
 lea heading_resets(pc),a1
 addq.l #1,(a1)
 rts
heading_reset_b:
 addq.l #6,a0
 move.l $32fb8,d0
 bsr.w FF1HeadingReset
 lea heading_resets(pc),a1
 addq.l #1,(a1)
 rts
heading_assign_b:
 move.l a0,a1
 addq.l #6,a0
 moveq #0,d0
 move.w $32fbc,d0
 lsl.l #2,d0
 lea $227aa,a2
 move.l (a2,d0.l),d0
 bsr.w FF1HeadingAssign
 lea heading_assignments(pc),a1
 addq.l #1,(a1)
 rts
heading_installed: dc.l 0
heading_steps: dc.l 0
heading_zeroes: dc.l 0
heading_resets: dc.l 0
heading_assignments: dc.l 0
heading_shadow: ds.b 96
'''
extra+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Heading.s')+'"\n'
asm+=extra+'fine_records: ds.b 25600\nheading_records: ds.b 38400\n'
(o/'hooks.json').write_text(json.dumps(hooks,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-position-fine/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge'),(9,'heading')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built heading + position diagnostic with',len(hooks),'heading sites')
