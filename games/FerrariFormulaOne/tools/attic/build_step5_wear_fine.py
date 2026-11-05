from pathlib import Path
import struct,subprocess,hashlib,json,re
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-wear-fine';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
# The exact-multiply pass runs before this installation. Preserve its MULS.L/NOP.
m=bytearray(m)
for a in (0x6de74,0x6defa):
 assert m[a:a+6]==bytes.fromhex('4eb900029500')
 m[a:a+6]=bytes.fromhex('4c0108004e71')
asm=(r/'tmp/build/step5-steering-fine/fine.s').read_text().replace('modeval: dc.w 8','modeval: dc.w MODE').replace(' bsr.w install_steering\n',' bsr.w install_steering\n bsr.w install_wear\n',1)
body,buffers=asm.split('velocity_records: ds.b 64000',1)
# address, displaced bytes, bytes before callback, rate register (or reset)
hooks=[(0x6de74,6,6,'d0'),(0x6defa,6,6,'d0'),(0x6de96,6,4,'d1'),(0x6ded4,6,4,'d1'),(0x6df2a,8,6,'d1'),(0x6e018,10,0,'d0'),(0x64b4c,6,2,'reset'),(0x687f4,6,0,'reset'),(0x6c67c,6,6,'reset')]
existing=json.loads((r/'tmp/build/step5-steering-fine/hooks.json').read_text())
for a,n,*_ in hooks:
 for b,k,*_ in existing:assert a+n<=b or b+k<=a,(hex(a),hex(b))
for line in (r/'tmp/step4/active.dis').read_text().splitlines():
 match=re.match(r'([0-9a-f]{6}):\s+[0-9a-f]+\s+(\S+)\s+\$([0-9a-f]+)',line)
 if match and (match[2].startswith('b') or match[2] in ('jmp','jsr')):
  pc,target=int(match[1],16),int(match[3],16);assert not any(a<target<a+n and not a<=pc<a+n for a,n,*_ in hooks),line
extra='''install_wear:
 movem.l d0-d7/a0-a6,-(sp)
 cmpi.w #7,d0
 blo.w .done
'''
for a,n,*_ in hooks:
 for k in range(0,n,2):extra+=f' cmpi.w #${m[a+k:a+k+2].hex()},${a+k:x}\n bne.w .bad\n'
for a,n,*_ in hooks:
 extra+=f' lea (wear_{a:x}.l,pc),a0\n move.w #$4ef9,${a:x}\n move.l a0,${a+2:x}\n'
 for k in range(6,n,2):extra+=f' move.w #$4e71,${a+k:x}\n'
extra+=''' lea wear_installed(pc),a0
 move.l #1,(a0)
 bra.b .done
.bad:
 lea error(pc),a0
 move.l #28,(a0)
.done:
 movem.l (sp)+,d0-d7/a0-a6
 rts
'''
def original(a,n):return (' dc.w '+','.join('$'+m[a+k:a+k+2].hex() for k in range(0,n,2))+'\n') if n else ''
for a,n,prefix,kind in hooks:
 extra+=f'wear_{a:x}:\n'+original(a,prefix)+''' movem.l d0-d7/a0-a6,-(sp)
 move.w sr,-(sp)
'''
 if kind=='reset':extra+=' bsr.w wear_reset\n'
 else:extra+=f' move.l {kind},d4\n move.l #${a:x},d6\n moveq #{6 if kind=="d0" else 10},d7\n bsr.w wear_sample\n'
 extra+=' move.w (sp)+,ccr\n movem.l (sp)+,d0-d7/a0-a6\n'+original(a+prefix,n-prefix)+f' jmp ${a+n:x}\n'
extra+='''wear_context:
 move.l a0,d2
 subi.l #$66c52,d2
 cmpi.l #16,d2
 blo.b .player
 move.l a0,d2
 subi.l #$22356,d2
 cmpi.l #32,d2
 bhs.w velocity_fault
 addi.l #16,d2
.player:
 move.l d2,d3
 andi.l #3,d3
 bne.w velocity_fault
 lsr.l #1,d2
 lea wear_remainders(pc),a1
 adda.l d2,a1
 rts
wear_reset:
 cmpi.w #8,modeval(pc)
 bne.b .done
 bsr.w wear_context
 clr.w (a1)
 lea wear_resets(pc),a1
 addq.l #1,(a1)
.done:
 rts
wear_sample:
 cmpi.w #8,modeval(pc)
 bne.w .done
 bsr.w wear_context
 move.l wear_samples(pc),d2
 cmpi.l #4096,d2
 bhs.w velocity_fault
 lsl.l #5,d2
 lea (wear_records.l,pc),a4
 adda.l d2,a4
 move.l d6,(a4)
 move.l a0,4(a4)
 move.l (a0),8(a4)
 move.l d4,12(a4)
 move.w (a1),20(a4)
 move.l ticks(pc),24(a4)
 move.l d4,d0
 bsr.w FF1Wear20Delta
 tst.l d1
 bne.w velocity_fault
 move.l d0,16(a4)
 move.w (a1),22(a4)
 move.l d0,(sp,d7.l)
 lea wear_samples(pc),a1
 addq.l #1,(a1)
.done:
 rts
wear_installed: dc.l 0
wear_samples: dc.l 0
wear_resets: dc.l 0
wear_remainders: ds.w 12
'''
extra+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Wear.s')+'"\n'
asm=body+extra+'velocity_records: ds.b 64000'+buffers+'wear_records: ds.b 131072\n'
(o/'hooks.json').write_text(json.dumps(existing+hooks,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-steering-fine/original_div.bin').read_bytes())
for mode,name in ((6,'control'),(7,'bridge'),(8,'fine')):
 (o/(name+'.s')).write_text(asm.replace('MODE',str(mode)))
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
 code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built combined motion, steering and continuous slip wear')
