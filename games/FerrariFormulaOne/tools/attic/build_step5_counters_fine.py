from pathlib import Path
import struct,subprocess,hashlib,json,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-counters-fine';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm=(r/'tmp/build/step5-clocks-fine/fine.s').read_text().replace('modeval: dc.w 8','modeval: dc.w MODE').replace(' bsr.w install_clocks\n',' bsr.w install_clocks\n bsr.w install_counters\n',1)
body,buffers=asm.split('velocity_records: ds.b 64000',1)
hooks=[(0x6712e,6,'phase'),(0x67172,8,'countdown'),(0x6734e,10,'clutch'),(0x673a4,6,'clutch_end')]
existing=json.loads((r/'tmp/build/step5-clocks-fine/hooks.json').read_text())
for a,n,*_ in hooks:
 for b,k,*_ in existing:assert a+n<=b or b+k<=a,(hex(a),hex(b))
for line in (r/'tmp/step4/active.dis').read_text().splitlines():
 match=re.match(r'([0-9a-f]{6}):\s+[0-9a-f]+\s+(\S+)\s+\$([0-9a-f]+)',line)
 if match and (match[2].startswith('b') or match[2] in ('jmp','jsr')):
  pc,target=int(match[1],16),int(match[3],16);assert not any(a<target<a+n and not a<=pc<a+n for a,n,*_ in hooks),line
extra="""install_counters:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
"""
for a,n,*_ in hooks:
 for k in range(0,n,2):extra+=f' cmpi.w #${m[a+k:a+k+2].hex()},${a+k:x}\n bne.w .bad\n'
for a,n,*_ in hooks:
 extra+=f' lea (counters_{a:x}.l,pc),a0\n move.w #$4ef9,${a:x}\n move.l a0,${a+2:x}\n'
 for k in range(6,n,2):extra+=f' move.w #$4e71,${a+k:x}\n'
extra+=""" lea counters_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #31,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
"""
def original(a,n):return ' dc.w '+','.join('$'+m[a+k:a+k+2].hex() for k in range(0,n,2))+'\n'
for a,n,kind in hooks:
 if kind=='clutch_end':
  extra+=f'counters_{a:x}:\n'+""" movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 moveq #2,d6
 bsr.w counters_after
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
"""+original(a,n)+f' jmp ${a+n:x}\n'
  continue
 index={'phase':0,'countdown':1,'clutch':2}[kind]
 extra+=f'counters_{a:x}:\n'+f""" movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 moveq #{index},d6
 bsr.w counters_before
 tst.w d0
 beq.b .skip
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
"""
 if kind=='clutch':
  extra+=original(a,n)+f' jmp ${a+n:x}\n'+""".skip:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
 jmp $673a4
"""
 else:
  extra+=original(a,n)+""" bra.b .record
.skip:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-d7/a0-a6
"""
  # Skipped countdown must retain nonzero NZ, with the native MOVE flags.
  if kind=='countdown':extra+=' move.w d0,$66f94\n'
  else:extra+=' andi.b #3,d0\n'
  extra+=f""".record:
 movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
 moveq #{index},d6
"""
  if kind=='phase':extra+=' move.b d0,$1be42\n'
  extra+=' bsr.w counters_after\n move.w (sp)+,ccr\n movem.l (sp)+,d0-d7/a0-a6\n'+f' jmp ${a+n:x}\n'
extra+="""counters_record:
 move.l counters_samples(pc),d0
 cmpi.l #400,d0
 bhs.w velocity_fault
 lsl.l #4,d0
 lea (counters_records.l,pc),a4
 adda.l d0,a4
 rts
counters_value:
 moveq #0,d0
 tst.w d6
 bne.b .word
 move.b $1be42,d0
 rts
.word:
 move.w $66f94,d0
 cmpi.w #1,d6
 beq.b .done
 move.w $32f2e,d0
.done:
 rts
counters_before:
 bsr.w counters_record
 move.l ticks(pc),(a4)
 move.w d6,4(a4)
 bsr.w counters_value
 move.w d0,8(a4)
 moveq #1,d0
 cmpi.w #8,modeval(pc)
 bne.b .decided
 move.w events_pulse(pc),d0
.decided:
 move.w d0,6(a4)
 rts
counters_after:
 bsr.w counters_record
 bsr.w counters_value
 move.w d0,10(a4)
 lea counters_samples(pc),a0
 addq.l #1,(a0)
 rts
counters_installed: dc.l 0
counters_samples: dc.l 0
"""
asm=body+extra+'velocity_records: ds.b 64000'+buffers+'counters_records: ds.b 6400\n'
(o/'hooks.json').write_text(json.dumps(existing+hooks,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-clocks-fine/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge'),(8,'fine')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built native cadence counters')
