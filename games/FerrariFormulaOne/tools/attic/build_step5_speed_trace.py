from pathlib import Path
import struct,subprocess,hashlib,json,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-speed-trace';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
asm=(r/'tmp/build/step5-math-v6/logic.s').read_text().replace('modeval: dc.w 6','modeval: dc.w MODE').replace(' cmpi.w #6,d0\n bne.b keep_gauges',' cmpi.w #6,d0\n blo.b keep_gauges').replace('keep_gauges:\n','keep_gauges:\n bsr.w install_velocity\n')
hooks=[(0x671e6,6,'load'),(0x685a6,6,'store'),(0x67bcc,8,'rotate'),(0x6dc96,6,'project'),(0x6dd44,6,'raw'),(0x6e084,6,'limit'),(0x6e2ae,8,'returned'),(0x68990,6,'cold_x'),(0x689a0,6,'cold_z'),(0x68b98,6,'cold_x'),(0x68baa,8,'cold_z200'),(0x6e95e,10,'cold_x'),(0x6e968,6,'cold_z'),(0x6917a,6,'swap_z'),(0x68386,6,'reset_work'),(0x6e2a4,6,'reset_work'),(0x6e2ec,6,'reset_work'),(0x69b36,6,'clamp_z'),(0x69b50,6,'clamp_z'),(0x6ee00,6,'impulse_x'),(0x6ee16,8,'impulse_x'),(0x6993a,6,'offroad_right'),(0x69a0a,6,'offroad_left'),(0x6998e,6,'offroad_z'),(0x69a5e,6,'offroad_z')]

speed_writers=[]
for line in (r/'tmp/step4/active.dis').read_text().splitlines():
 match=re.match(r'([0-9a-f]{6}):\s+([0-9a-f]+)\s+move.w ([^,]+), \$32fbe.l',line)
 if match:
  a=int(match[1],16);n=len(match[2])//2
  assert n>=6
  speed_writers.append(a);hooks.append((a,n,'speed_'+hex(a)[2:]))

for line in (r/'tmp/step4/active.dis').read_text().splitlines():
 match=re.match(r'([0-9a-f]{6}):\s+[0-9a-f]+\s+(\S+)\s+\$([0-9a-f]+)',line)
 if match and (match[2].startswith('b') or match[2] in ('jmp','jsr')):
  pc,target=int(match[1],16),int(match[3],16);assert not any(a<target<a+n and not a<=pc<a+n for a,n,_ in hooks),line
extra='''install_velocity:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
'''
for a,n,_ in hooks:
 for k in range(0,n,2):extra+=f' cmpi.w #${m[a+k:a+k+2].hex()},${a+k:x}\n bne.w .bad\n'
for a,n,_ in hooks:
 extra+=f' lea velocity_{a:x}(pc),a0\n move.w #$4ef9,${a:x}\n move.l a0,${a+2:x}\n'
 for k in range(6,n,2):extra+=f' move.w #$4e71,${a+k:x}\n'
extra+=''' lea velocity_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #16,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
'''
for a,n,action in hooks:
 original=' dc.w '+','.join('$'+m[a+k:a+k+2].hex() for k in range(0,n,2))+'\n'
 callback=f' movem.l d0-d7/a0-a6,-(sp)\n move.w sr,-(sp)\n move.l d0,d7\n bsr.w velocity_{action}\n move.w (sp)+,ccr\n movem.l (sp)+,d0-d7/a0-a6\n'
 before=action.startswith('cold_') or action in ('swap_z','impulse_x')
 extra+=f'velocity_{a:x}:\n'+(callback+original if before else original+callback)+f' jmp ${a+n:x}\n'
extra+='''velocity_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 bhi.w velocity_fault
 mulu.w #12,d0
 lea velocity_shadow(pc),a0
 adda.l d0,a0
 rts
velocity_sync:
 bsr.w velocity_context
 move.w $32f94,d0
 move.w $32f96,d1
 bsr.w FF1VelocityReset
 rts
velocity_load:
 lea velocity_loads(pc),a1
 addq.l #1,(a1)
 cmpi.w #8,modeval(pc)
 bne.w velocity_sync
 bsr.w velocity_context
 move.w $32fbc,d2
 lea velocity_initialized(pc),a1
 bset d2,(a1)
 bne.w velocity_check
 bsr.w velocity_sync
 clr.l 8(a0)
 rts
velocity_store:
 lea velocity_stores(pc),a1
 addq.l #1,(a1)
 cmpi.w #8,modeval(pc)
 bne.w velocity_sync
 bsr.w velocity_context
 bra.w velocity_check
velocity_rotate:
 lea velocity_rotations(pc),a1
 addq.l #1,(a1)
 cmpi.w #8,modeval(pc)
 bne.w velocity_sync
 bsr.w velocity_context
 lea 8(a0),a1
 moveq #0,d2
 move.w -16(a6),d2
 andi.l #1023,d2
 add.l d2,d2
 lea $2180c,a2
 move.w (a2,d2.l),d1
 lea $21a0c,a2
 move.w (a2,d2.l),d0
 bsr.w FF1VelocityRotateCarry020
 tst.l d1
 bne.w velocity_fault
 move.w (a0),$32f94
 move.w 4(a0),$32f96
 rts
velocity_check:
 move.w (a0),d0
 cmp.w $32f94,d0
 bne.w velocity_fault_x
 move.w 4(a0),d0
 cmp.w $32f96,d0
 bne.w velocity_fault_z
 rts
velocity_record:
 move.l velocity_records_count(pc),d0
 cmpi.l #800,d0
 bhs.w velocity_fault
 mulu.w #80,d0
 lea velocity_records(pc),a4
 adda.l d0,a4
 rts
velocity_project:
 bsr.w velocity_record
 move.w $32fbc,(a4)
 move.w 10(a6),2(a4)
 move.w 14(a6),4(a4)
 move.w -14(a6),8(a4)
 move.w -16(a6),10(a4)
 move.w $32f94,12(a4)
 move.w $32f96,14(a4)
 moveq #0,d0
 move.w 10(a6),d0
 andi.l #1023,d0
 add.l d0,d0
 lea $2180c,a0
 move.w (a0,d0.l),d1
 lea $21a0c,a0
 move.w (a0,d0.l),d2
 move.w 14(a6),d0
 swap d0
 clr.w d0
 lea 24(a4),a0
 bsr.w FF1VelocityProject020
 tst.l d1
 bne.w velocity_fault
 bsr.w velocity_context
 move.l (a0),40(a4)
 move.l 4(a0),44(a4)
 move.l 8(a0),48(a4)
 lea 40(a4),a0
 lea 24(a4),a1
 lea 52(a4),a2
 bsr.w FF1VelocityDerivative20
 tst.l d1
 bne.w velocity_fault
 ; Old physical velocity is Q16 + carry/5: normalized delta subtracts carry.
 move.w 48(a4),d0
 ext.l d0
 sub.l d0,52(a4)
 bvs.w velocity_fault
 move.w 50(a4),d0
 ext.l d0
 sub.l d0,56(a4)
 bvs.w velocity_fault
 bsr.w velocity_coefficients
 lea 52(a4),a0
 bsr.w FF1VelocityRotate020
 tst.l d1
 bne.w velocity_fault
 lea velocity_projects(pc),a0
 addq.l #1,(a0)
 rts
velocity_raw:
 bsr.w velocity_record
 cmpi.w #8,modeval(pc)
 bne.b .native
 move.w 52(a4),-12(a6)
 move.w 56(a4),-10(a6)
 move.w -12(a6),d0
 muls.w d0,d0
 move.w -10(a6),d1
 muls.w d1,d1
 add.l d1,d0
 bsr.w FF1SquareRootU32
 cmpi.l #32767,d0
 bhi.w velocity_fault
 move.l d0,d7
 move.l d0,6(sp)
.native:
 move.w -12(a6),32(a4)
 move.w -10(a6),34(a4)
 move.w d7,36(a4)
 lea velocity_raws(pc),a0
 addq.l #1,(a0)
 rts
velocity_limit:
 cmpi.w #8,modeval(pc)
 bne.b .done
 bsr.w velocity_record
 moveq #0,d2
 move.w 36(a4),d2
 beq.b .zero
 move.w -8(a6),38(a4)
 move.w 32(a4),d0
 move.w 38(a4),d1
 bsr.w FF1VelocityLimit020
 tst.l d1
 bne.w velocity_fault
 move.w d0,-12(a6)
 move.w 34(a4),d0
 move.w 38(a4),d1
 bsr.w FF1VelocityLimit020
 tst.l d1
 bne.w velocity_fault
 move.w d0,-10(a6)
 rts
.zero:
 clr.w 38(a4)
 clr.w -12(a6)
 clr.w -10(a6)
.done:
 rts
velocity_returned:
 bsr.w velocity_record
 move.w d7,6(a4)
 move.w $32f94,16(a4)
 move.w $32f96,18(a4)
 move.w -12(a6),20(a4)
 move.w -10(a6),22(a4)
 move.w 20(a4),d0
 swap d0
 clr.w d0
 move.l d0,60(a4)
 move.w 22(a4),d0
 swap d0
 clr.w d0
 move.l d0,64(a4)
 bsr.w velocity_coefficients
 neg.w d1
 lea 60(a4),a0
 bsr.w FF1VelocityRotate020
 tst.l d1
 bne.w velocity_fault
 move.l 40(a4),68(a4)
 move.l 44(a4),72(a4)
 move.l 48(a4),76(a4)
 lea 68(a4),a0
 lea 76(a4),a1
 lea 60(a4),a2
 bsr.w FF1VelocityApply20
 tst.l d1
 bne.w velocity_fault
 cmpi.w #8,modeval(pc)
 bne.b .native
 bsr.w velocity_context
 move.l 68(a4),(a0)
 move.l 72(a4),4(a0)
 move.l 76(a4),8(a0)
 move.w (a0),$32f94
 move.w 4(a0),$32f96
 move.w (a0),16(a4)
 move.w 4(a0),18(a4)
 move.w (a0),d0
 muls.w d0,d0
 move.w 4(a0),d1
 muls.w d1,d1
 add.l d1,d0
 move.l d0,-(sp)
 jsr $25770
 addq.l #4,sp
 cmpi.w #500,d0
 ble.b .speed
 move.w #500,d0
.speed:
 move.w d0,6(a4)
 move.l d0,6(sp)
.native:
 lea velocity_records_count(pc),a0
 addq.l #1,(a0)
 rts
velocity_coefficients:
 moveq #0,d2
 move.w 2(a4),d2
 andi.l #1023,d2
 add.l d2,d2
 lea $2180c,a0
 move.w (a0,d2.l),d1
 lea $21a0c,a0
 move.w (a0,d2.l),d0
 rts
velocity_fault_x:
 moveq #21,d0
 bra.b velocity_failcode
velocity_fault_z:
 moveq #22,d0
 bra.b velocity_failcode
velocity_fault:
 moveq #17,d0
velocity_failcode:
 lea error(pc),a0
 move.l d0,(a0)
velocity_stop:
 bra.b velocity_stop
velocity_initialized: dc.w 0
velocity_installed: dc.l 0
velocity_loads: dc.l 0
velocity_stores: dc.l 0
velocity_rotations: dc.l 0
velocity_projects: dc.l 0
velocity_raws: dc.l 0
velocity_records_count: dc.l 0
velocity_shadow: ds.b 96
'''
extra+='''velocity_cold_x:
 suba.l #$6f13c,a0
 moveq #0,d4
 moveq #0,d5
 bra.b velocity_cold
velocity_cold_z:
 moveq #0,d5
 bra.b velocity_cold_z_common
velocity_cold_z200:
 move.l #$00c80000,d5
velocity_cold_z_common:
 suba.l #$6f14c,a0
 moveq #4,d4
velocity_cold:
 move.l a0,d0
 bsr.w velocity_array_context
 move.l d5,(a0,d4.w)
 lsr.w #1,d4
 clr.w 8(a0,d4.w)
 lea velocity_cold_writes(pc),a0
 addq.l #1,(a0)
 rts
velocity_array_context:
 cmpi.l #14,d0
 bhi.w velocity_fault
 btst #0,d0
 bne.w velocity_fault
 mulu.w #6,d0
 lea velocity_shadow(pc),a0
 adda.l d0,a0
 rts
velocity_swap_z:
 move.l a0,d6
 subi.l #$6f14c,d6
 move.l d3,d0
 bsr.w velocity_array_context
 move.l a0,a2
 move.l d6,d0
 bsr.w velocity_array_context
 move.l 4(a0),d0
 move.w 10(a0),d1
 move.l 4(a2),4(a0)
 move.w 10(a2),10(a0)
 move.l d0,4(a2)
 move.w d1,10(a2)
 lea velocity_swaps(pc),a0
 addq.l #1,(a0)
 rts
velocity_cold_writes: dc.l 0
velocity_swaps: dc.l 0
'''
extra+='''velocity_reset_work:
 bsr.w velocity_sync
 clr.l 8(a0)
 lea velocity_work_resets(pc),a0
 addq.l #1,(a0)
 rts
velocity_clamp_z:
 bsr.w velocity_context
 move.w $32f96,4(a0)
 clr.w 6(a0)
 clr.w 10(a0)
 lea velocity_clamps(pc),a0
 addq.l #1,(a0)
 rts
velocity_impulse_x:
 ; D1 holds the newly computed native word; preserve fractional tail/carry.
 move.w d1,d4
 move.l a0,d0
 subi.l #$6f13c,d0
 bsr.w velocity_array_context
 move.w d4,(a0)
 lea velocity_impulses(pc),a0
 addq.l #1,(a0)
 rts
velocity_work_resets: dc.l 0
velocity_clamps: dc.l 0
velocity_impulses: dc.l 0
'''
extra+='''velocity_offroad_right:
 move.w $2aaa6,d4
 ext.l d4
 moveq #0,d5
 bra.b velocity_offroad
velocity_offroad_left:
 move.w $2aaa6,d4
 ext.l d4
 neg.l d4
 moveq #0,d5
 bra.b velocity_offroad
velocity_offroad_z:
 move.l d7,d4
 neg.l d4
 moveq #4,d5
velocity_offroad:
 bsr.w velocity_context
 cmpi.w #8,modeval(pc)
 beq.b .fine
 lea $32f94,a1
 move.w d5,d0
 lsr.w #1,d0
 move.w (a1,d0.w),(a0,d5.w)
 bra.b .count
.fine:
 cmpi.l #-32768,d4
 blt.w velocity_fault
 cmpi.l #32767,d4
 bgt.w velocity_fault
 swap d4
 clr.w d4
 suba.w #8,sp
 clr.l (sp)
 clr.l 4(sp)
 move.l d4,(sp,d5.w)
 move.l sp,a2
 lea 8(a0),a1
 bsr.w FF1VelocityApply20
 adda.w #8,sp
 tst.l d1
 bne.w velocity_fault
 move.w (a0),$32f94
 move.w 4(a0),$32f96
.count:
 lea velocity_offroads(pc),a0
 addq.l #1,(a0)
 rts
velocity_offroads: dc.l 0
'''
for module in ('Step','Velocity'):extra+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'

for a in speed_writers:
 extra+=f'velocity_speed_{a:x}:\n move.l #${a:x},d6\n bra.w velocity_speed_trace\n'
extra+='velocity_speed_trace:\n move.l velocity_speed_count(pc),d0\n lea velocity_speed_count(pc),a0\n addq.l #1,(a0)\n andi.l #511,d0\n lsl.l #4,d0\n lea velocity_speed_records(pc),a0\n adda.l d0,a0\n move.l d6,(a0)+\n move.l ticks(pc),(a0)+\n move.w $32fbc,(a0)+\n move.w $32fbe,(a0)+\n move.w d7,(a0)+\n move.w d1,(a0)+\n rts\nvelocity_speed_count: dc.l 0\nvelocity_speed_records: ds.b 8192\n'

asm+=extra+'velocity_records: ds.b 64000\n'
(o/'hooks.json').write_text(json.dumps(hooks,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-math-v6/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge'),(8,'fine')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built native velocity diagnostic')
