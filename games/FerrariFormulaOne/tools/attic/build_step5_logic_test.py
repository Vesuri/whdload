from pathlib import Path
import struct,subprocess,json,hashlib,math
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-logic-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
asm='''start:
 add.l $1c(a3),d0
 move.l d0,a1
 movem.l d0-a6,-(sp)
 move.w sr,-(sp)
 cmp.l #$64a68,d0
 bne.w done
 lea installed(pc),a0
 tst.l (a0)
 bne.w done
 addq.l #1,(a0)
 lea barrier(pc),a0
 move.l a0,$654e8
 bsr.w tests
done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
barrier: jmp $2a130
tests:
''';expected=[]
for i,(period,phase) in enumerate(((20,0),(20,40),(200,0),(200,40))):
 firsttick=math.ceil((700-phase)/period);firstfield=math.ceil(firsttick*709379*(period//20)/710510)
 expected.append([firstfield,firsttick,0xffffffff,50*20//period,phase])
 asm+=f''' lea context(pc),a0
 move.w #{period},d0
 bsr.w FF1TimeInit
 move.w #{phase},FF1T_PHASE_MS(a0)
 lea status(pc),a1
 move.w #-8,(a1)
 lea results+{i*20}(pc),a3
 moveq #49,d6
field{i}:
 bsr.w FF1TimeField
drain{i}:
 bsr.w FF1TimeDue
 tst.l d0
 beq.b next{i}
 bsr.w FF1TimeConsume
 move.l a0,a2
 lea status(pc),a0
 bsr.w FF1AdvanceRecovery
 move.l a2,a0
 cmpi.w #-1,d0
 bne.b drain{i}
 tst.l (a3)
 bne.b drain{i}
 move.l FF1T_FIELDS(a0),(a3)
 move.l FF1T_TICKS(a0),4(a3)
 bra.b drain{i}
next{i}:
 dbra d6,field{i}
 move.w status(pc),d0
 ext.l d0
 move.l d0,8(a3)
 move.l FF1T_TICKS(a0),12(a3)
 moveq #0,d0
 move.w FF1T_PHASE_MS(a0),d0
 move.l d0,16(a3)
'''
asm+=' rts\n include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Time.s')+'"\n include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Logic.s')+'"\ninstalled: dc.l 0\nstatus: dc.w 0\ncontext: ds.b FF1T_SIZE\nresults: ds.l 20\n'
(o/'test.s').write_text(asm);(o/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-Fbin','-quiet','-L','test.list','-o','test.bin','test.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(normal)-pos-2)+bytes.fromhex('4e71');code+=(o/'test.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'test.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print('Built timer-driven recovery tests at both intervals and clock phases')
