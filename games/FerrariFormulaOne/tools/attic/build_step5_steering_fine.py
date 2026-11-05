from pathlib import Path
import struct,subprocess,hashlib,json,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-steering-fine';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-motion-fine/fine.s').read_text().replace('modeval: dc.w 8','modeval: dc.w MODE').replace(' bsr.w install_heading\n',' bsr.w install_heading\n bsr.w install_steering\n',1)
body,buffers=asm.split('velocity_records: ds.b 64000',1)
hooks=[(0x6773c,6,'sample'),(0x68788,10,'reset')]
existing=json.loads((r/'tmp/build/step5-motion-fine/hooks.json').read_text())
for a,n,_ in hooks:
 for b,k,*_ in existing:assert a+n<=b or b+k<=a,(hex(a),hex(b))
for line in (r/'tmp/step4/active.dis').read_text().splitlines():
 match=re.match(r'([0-9a-f]{6}):\s+[0-9a-f]+\s+(\S+)\s+\$([0-9a-f]+)',line)
 if match and (match[2].startswith('b') or match[2] in ('jmp','jsr')):
  pc,target=int(match[1],16),int(match[3],16);assert not any(a<target<a+n and not a<=pc<a+n for a,n,_ in hooks),line
extra='''install_steering:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
'''
for a,n,_ in hooks:
 for k in range(0,n,2):extra+=f' cmpi.w #${m[a+k:a+k+2].hex()},${a+k:x}\n bne.w .bad\n'
for a,n,_ in hooks:
 extra+=f' lea (steering_{a:x}.l,pc),a0\n move.w #$4ef9,${a:x}\n move.l a0,${a+2:x}\n'
 for k in range(6,n,2):extra+=f' move.w #$4e71,${a+k:x}\n'
extra+=''' lea steering_shadow(pc),a0
 lea $32f7a,a1
 move.l ticks(pc),d3
 subq.l #1,d3
 moveq #7,d7
.init:
 move.w (a1)+,d0
 bsr.w FF1SteeringReset
 adda.w #18,a0
 dbra d7,.init
 lea steering_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #27,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
'''
for a,n,kind in hooks:
 original=' dc.w '+','.join('$'+m[a+k:a+k+2].hex() for k in range(0,n,2))+'\n'
 if kind=='sample':
  # Test mode while preserving native flags; inactive mode executes exact bytes.
  extra+=f'''steering_{a:x}:
 move.w sr,-(sp)
 cmpi.w #8,modeval(pc)
 beq.b .fine
 move.w (sp)+,ccr
'''+original+f''' jmp ${a+n:x}
.fine:
 move.w (sp)+,ccr
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 move.l d0,d4
 move.l a0,a5
 bsr.w steering_sample
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp ${a+n:x}
'''
 else:extra+=f'''steering_{a:x}:
'''+original+f''' movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 bsr.w steering_reset
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp ${a+n:x}
'''
extra+='''steering_context:
 moveq #0,d0
 move.w $32fbc,d0
 cmpi.w #7,d0
 bhi.w velocity_fault
 mulu.w #18,d0
 lea steering_shadow(pc),a0
 adda.l d0,a0
 rts
steering_sample:
 bsr.w steering_context
 move.l steering_samples(pc),d0
 cmpi.l #800,d0
 bhs.w velocity_fault
 mulu.w #20,d0
 lea (steering_records.l,pc),a4
 adda.l d0,a4
 move.l ticks(pc),d3
 move.l d3,(a4)
 move.w $32fbc,4(a4)
 move.w d4,6(a4)
 move.l 12(a0),12(a4)
 sub.l 12(a0),d3
 move.l d3,16(a4)
 move.l ticks(pc),d3
 move.w d4,d0
 bsr.w FF1SteeringSample20
 tst.l d1
 bne.w velocity_fault
 move.w d2,8(a4)
 move.w d0,10(a4)
 move.w d0,12(sp)
 move.w d0,(a5)
 move.w sr,d5
 andi.w #15,d5
 move.w d4,d6
 add.w d2,d6
 andi.w #1,d6
 lsl.w #4,d6
 or.w d6,d5
 andi.w #$ffe0,4(sp)
 or.w d5,4(sp)
 lea steering_samples(pc),a0
 addq.l #1,(a0)
 rts
steering_reset:
 cmpi.w #8,modeval(pc)
 bne.b .done
 bsr.w steering_context
 moveq #0,d0
 move.l ticks(pc),d3
 subq.l #1,d3
 bsr.w FF1SteeringReset
 lea steering_resets(pc),a0
 addq.l #1,(a0)
.done:
 rts
steering_installed: dc.l 0
steering_samples: dc.l 0
steering_resets: dc.l 0
steering_shadow: ds.b 144
'''
extra+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Steering.s')+'"\n'
asm=body+extra+'velocity_records: ds.b 64000'+buffers+'steering_records: ds.b 16000\n'
(o/'hooks.json').write_text(json.dumps(existing+hooks,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-motion-fine/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge'),(8,'fine')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built combined motion with 100 ms steering history')
