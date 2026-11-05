from pathlib import Path
import struct,subprocess,hashlib,json,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-clocks-fine';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-events-fine/fine.s').read_text().replace('modeval: dc.w 8','modeval: dc.w MODE').replace(' bsr.w install_events\n',' bsr.w install_events\n bsr.w install_clocks\n',1)
body,buffers=asm.split('velocity_records: ds.b 64000',1)
hooks=[(0x65dca,6,'session'),(0x65dd8,6,'race')]
existing=json.loads((r/'tmp/build/step5-events-fine/hooks.json').read_text())
for a,n,*_ in hooks:
 for b,k,*_ in existing:assert a+n<=b or b+k<=a,(hex(a),hex(b))
for line in (r/'tmp/step4/active.dis').read_text().splitlines():
 match=re.match(r'([0-9a-f]{6}):\s+[0-9a-f]+\s+(\S+)\s+\$([0-9a-f]+)',line)
 if match and (match[2].startswith('b') or match[2] in ('jmp','jsr')):
  pc,target=int(match[1],16),int(match[3],16);assert not any(a<target<a+n and not a<=pc<a+n for a,n,*_ in hooks),line
extra='''install_clocks:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
'''
for a,n,*_ in hooks:
 for k in range(0,n,2):extra+=f' cmpi.w #${m[a+k:a+k+2].hex()},${a+k:x}\n bne.w .bad\n'
for a,n,*_ in hooks:extra+=f' lea (clocks_{a:x}.l,pc),a0\n move.w #$4ef9,${a:x}\n move.l a0,${a+2:x}\n'
extra+=''' lea clocks_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #30,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
'''
for a,n,kind in hooks:
 extra+=f'''clocks_{a:x}:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 moveq #{int(kind=='race')},d6
 bsr.w clocks_before
 tst.w d0
 beq.b .skip
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jsr $22c3a
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
.skip:
 bsr.w clocks_after
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp ${a+n:x}
'''
extra+='''clocks_record:
 move.l clocks_samples(pc),d0
 cmpi.l #200,d0
 bhs.w velocity_fault
 lsl.l #5,d0
 lea (clocks_records.l,pc),a4
 adda.l d0,a4
 rts
clocks_pointer:
 lea $226c0,a0
 tst.w 4(a4)
 beq.b .done
 adda.w #10,a0
.done:
 rts
clocks_before:
 bsr.w clocks_record
 move.l ticks(pc),(a4)
 move.w d6,4(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .decided
 move.w events_pulse(pc),d0
.decided:
 move.w d0,6(a4)
 bsr.w clocks_pointer
 move.l (a0)+,8(a4)
 move.l (a0)+,12(a4)
 move.w (a0),16(a4)
 move.w 6(a4),d0
 rts
clocks_after:
 bsr.w clocks_record
 bsr.w clocks_pointer
 move.l (a0)+,18(a4)
 move.l (a0)+,22(a4)
 move.w (a0),26(a4)
 lea clocks_samples(pc),a0
 addq.l #1,(a0)
 rts
clocks_installed: dc.l 0
clocks_samples: dc.l 0
'''
asm=body+extra+'velocity_records: ds.b 64000'+buffers+'clocks_records: ds.b 6400\n'
(o/'hooks.json').write_text(json.dumps(existing+hooks,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-events-fine/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge'),(8,'fine')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built eligible native clock pulse gate')
