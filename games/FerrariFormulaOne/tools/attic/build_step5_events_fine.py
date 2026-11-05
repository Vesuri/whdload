from pathlib import Path
import struct,subprocess,hashlib,json,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-events-fine';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-wear-fine/fine.s').read_text().replace('modeval: dc.w 8','modeval: dc.w MODE').replace(' bsr.w install_wear\n',' bsr.w install_wear\n bsr.w install_events\n',1)
# Diagnostic physics steps represent exactly 20 ms. The production scheduler
# must supply its native-tenth pulse instead; never use rendered frames here.
asm=asm.replace('finish:\n','finish:\n bsr.w events_quantum\n',1)
body,buffers=asm.split('velocity_records: ds.b 64000',1)
hooks=[(0x6d5f2,8,'player'),(0x6d67e,6,'opponent'),(0x24eec,10,'rng')]
existing=json.loads((r/'tmp/build/step5-wear-fine/hooks.json').read_text())
for a,n,*_ in hooks:
 for b,k,*_ in existing:assert a+n<=b or b+k<=a,(hex(a),hex(b))
for line in (r/'tmp/step4/active.dis').read_text().splitlines():
 match=re.match(r'([0-9a-f]{6}):\s+[0-9a-f]+\s+(\S+)\s+\$([0-9a-f]+)',line)
 if match and (match[2].startswith('b') or match[2] in ('jmp','jsr')):
  pc,target=int(match[1],16),int(match[3],16);assert not any(a<target<a+n and not a<=pc<a+n for a,n,*_ in hooks),line
extra='''install_events:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
'''
for a,n,*_ in hooks:
 for k in range(0,n,2):extra+=f' cmpi.w #${m[a+k:a+k+2].hex()},${a+k:x}\n bne.w .bad\n'
for a,n,*_ in hooks:
 extra+=f' lea (events_{a:x}.l,pc),a0\n move.w #$4ef9,${a:x}\n move.l a0,${a+2:x}\n'
 for k in range(6,n,2):extra+=f' move.w #$4e71,${a+k:x}\n'
extra+=''' lea events_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #29,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
events_quantum:
 cmpi.l #126,ticks(pc)
 blo.b .done
 cmpi.w #8,modeval(pc)
 bne.b .done
 lea events_phase(pc),a0
 clr.w 2(a0)
 addq.w #1,(a0)
 cmpi.w #5,(a0)
 blo.b .done
 clr.w (a0)
 move.w #1,2(a0)
 lea events_pulses(pc),a0
 addq.l #1,(a0)
.done:
 rts
'''
for a,n,kind in hooks[:2]:
 extra+=f'''events_{a:x}:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 moveq #{0 if kind=='player' else 1},d6
 bsr.w events_before
 tst.w d0
 beq.b .skip
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jsr ${0x6ea3e if kind=='player' else 0x6ee70:x}
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
.skip:
 bsr.w events_after
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
'''
 if kind=='opponent':extra+=' addq.l #4,sp\n'
 extra+=' jmp $6d684\n'
extra+='''events_24eec:
 move.w sr,-(sp)
 move.l a0,-(sp)
 lea events_rng_calls(pc),a0
 addq.l #1,(a0)
 move.l (sp)+,a0
 move.w (sp)+,ccr
'''
extra+=' dc.w '+','.join('$'+m[0x24eec+k:0x24eee+k].hex() for k in range(0,10,2))+'\n jmp $24ef6\n'
# 160-byte record: header32, condition/status snapshot64 before and after.
extra+='''events_record:
 move.l events_samples(pc),d0
 cmpi.l #800,d0
 bhs.w velocity_fault
 mulu.w #160,d0
 lea (events_records.l,pc),a4
 adda.l d0,a4
 rts
events_before:
 bsr.w events_record
 move.l ticks(pc),(a4)
 move.w $32fbc,4(a4)
 move.w d6,6(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .decided
 move.w events_pulse(pc),d0
.decided:
 move.w d0,8(a4)
 move.w $6ef52,10(a4)
 move.l events_rng_calls(pc),16(a4)
 lea 32(a4),a1
 bsr.w events_snapshot
 move.w 8(a4),d0
 rts
events_after:
 bsr.w events_record
 move.w $6ef52,12(a4)
 move.l events_rng_calls(pc),20(a4)
 lea 96(a4),a1
 bsr.w events_snapshot
 lea events_samples(pc),a0
 addq.l #1,(a0)
 rts
events_snapshot:
 lea $66c3e,a0
 moveq #13,d0
.copy:
 move.l (a0)+,(a1)+
 dbra d0,.copy
 moveq #0,d0
 move.w $32fbc,d0
 add.w d0,d0
 move.w $2268e(d0.l),(a1)+
 move.w $2269e(d0.l),(a1)+
 add.w d0,d0
 move.l $6f10a(d0.l),(a1)+
 rts
events_installed: dc.l 0
events_samples: dc.l 0
events_rng_calls: dc.l 0
events_pulses: dc.l 0
events_phase: dc.w 0
events_pulse: dc.w 0
'''
asm=body+extra+'velocity_records: ds.b 64000'+buffers+'events_records: ds.b 128000\n'
(o/'hooks.json').write_text(json.dumps(existing+hooks,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-wear-fine/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge'),(8,'fine')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built rotating wear / random-failure pulse gate')
