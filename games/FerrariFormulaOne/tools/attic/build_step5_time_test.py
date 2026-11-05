from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-time-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=bytearray(base[32:-4]);size=len(normal)
assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
core=r.parent.parent/'Games/FerrariFormulaOne_Time.s'
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
barrier:
 jmp $2a130
tests:
'''
expected=[]
# Directly exercise both intervals, delayed service, two-tick service batches,
# counter/low-word wrap, preserved fractional clock phase, and pause rebase.
for i,(ms,fields,batch,wrap) in enumerate(((20,6000,0,False),(200,6000,0,False),(20,6000,2,False),(200,6000,2,False),(20,120,0,True),(200,120,0,True))):
 quantum=709379*(ms//20);initial=(5<<32)+0xffffff00 if wrap else 0
 initialfields=0xfffffff0 if wrap else 0
 initialphase=40 if wrap else 0
 asm+=f''' lea context(pc),a0
 move.w #{ms},d0
 bsr.w FF1TimeInit
'''
 if wrap:asm+=''' move.l #$fffffff0,FF1T_FIELDS(a0)
 move.l #5,FF1T_ELAPSED_HI(a0)
 move.l #$ffffff00,FF1T_ELAPSED_LO(a0)
 move.l #5,FF1T_CONSUMED_HI(a0)
 move.l #$ffffff00,FF1T_CONSUMED_LO(a0)
 move.w #40,FF1T_PHASE_MS(a0)
'''
 asm+=f''' move.l #{fields-1},d6
 moveq #0,d7
case{i}_field:
 bsr.w FF1TimeField
 moveq #{batch or 100},d5
case{i}_drain:
 bsr.w FF1TimeDue
 tst.l d0
 beq.b case{i}_next
 bsr.w FF1TimeConsume
 add.l d0,d7
 subq.w #1,d5
 bne.b case{i}_drain
case{i}_next:
 dbra d6,case{i}_field
 lea results+{i*60}(pc),a1
 moveq #13,d4
case{i}_copy:
 move.l (a0)+,(a1)+
 dbra d4,case{i}_copy
 move.l d7,(a1)
'''
 ticks=fields*710510//quantum;elapsed=initial+fields*710510;consumed=initial+ticks*quantum
 expected.append({'case':i,'interval_ms':ms,'fields':fields,'batch_limit':batch,'expected':[ (initialfields+fields)&0xffffffff,elapsed>>32,elapsed&0xffffffff,consumed>>32,consumed&0xffffffff,quantum,ticks,(((initialphase+ticks*ms)%100)<<16)|ms,0,0,0,(initialphase+ticks*ms)//100]})
# Preserving the accumulated fraction through a long pause.
i=6
asm+=''' lea context(pc),a0
 moveq #20,d0
 bsr.w FF1TimeInit
 moveq #2,d6
pause_before:
 bsr.w FF1TimeField
 bsr.w FF1TimeConsume
 dbra d6,pause_before
 bsr.w FF1TimeRebase
 move.w #999,d6
pause_fields:
 bsr.w FF1TimeField
 dbra d6,pause_fields
 bsr.w FF1TimeRebase
 bsr.w FF1TimeDue
 lea pause_due(pc),a1
 move.l d0,(a1)
 moveq #1,d6
 moveq #0,d7
pause_after:
 bsr.w FF1TimeField
 bsr.w FF1TimeConsume
 add.l d0,d7
 dbra d6,pause_after
 lea results+360(pc),a1
 moveq #13,d4
pause_copy:
 move.l (a0)+,(a1)+
 dbra d4,pause_copy
 move.l d7,(a1)
 lea context(pc),a0
 bsr.w FF1TimeConsume
 lea early_result(pc),a1
 move.l d0,(a1)
 moveq #33,d0
 bsr.w FF1TimeInit
 lea unsupported_result(pc),a1
 move.l d0,(a1)
 rts
'''
elapsed=1005*710510;consumed=1003*710510+2*709379;rebased=1003*710510-3*709379
expected.append({'case':6,'interval_ms':20,'pause_fields':1000,'expected':[1005,elapsed>>32,elapsed&0xffffffff,consumed>>32,consumed&0xffffffff,709379,5,20,2,rebased>>32,rebased&0xffffffff,1]})
for e in expected:
 e['expected'][-1:-1]=[0,0,0]
# A real pause retains both whole pending work and sub-tick active time.
asm=asm.removesuffix(' rts\n')
asm+=''' lea context(pc),a0
 moveq #20,d0
 bsr.w FF1TimeInit
 moveq #1,d6
real_before:
 bsr.w FF1TimeField
 bsr.w FF1TimeConsume
 dbra d6,real_before
 bsr.w FF1TimeField
 bsr.w FF1TimePause
 bsr.w FF1TimePause
 lea repeated_pause(pc),a1
 move.l d0,(a1)
 move.w #999,d6
real_pause_fields:
 bsr.w FF1TimeField
 dbra d6,real_pause_fields
 bsr.w FF1TimeConsume
 lea paused_consume(pc),a1
 move.l d0,(a1)
 bsr.w FF1TimeResume
 bsr.w FF1TimeResume
 lea repeated_resume(pc),a1
 move.l d0,(a1)
 bsr.w FF1TimeConsume
 move.l d0,d7
 moveq #1,d6
real_after:
 bsr.w FF1TimeField
 bsr.w FF1TimeConsume
 add.l d0,d7
 dbra d6,real_after
 lea results+420(pc),a1
 moveq #13,d4
real_copy:
 move.l (a0)+,(a1)+
 dbra d4,real_copy
 move.l d7,(a1)
 lea context(pc),a0
 bsr.w FF1TimeConsume
 moveq #33,d0
 bsr.w FF1TimeInit
 rts
'''
elapsed=1005*710510;excluded=1000*710510;consumed=excluded+5*709379
expected.append({'case':7,'interval_ms':20,'pause_fields':1000,'expected':[1005,elapsed>>32,elapsed&0xffffffff,consumed>>32,consumed&0xffffffff,709379,5,20,1,excluded>>32,excluded&0xffffffff,0,0,0,1]})
asm+='repeated_pause: dc.l -1\nrepeated_resume: dc.l -1\npaused_consume: dc.l 0\n'
asm+=f' include "{core}"\ninstalled: dc.l 0\npause_due: dc.l -1\nearly_result: dc.l 0\nunsupported_result: dc.l -1\ncontext: ds.b FF1T_SIZE\nresults: ds.b 8*60\n'
(o/'test.s').write_text(asm);(o/'expected.json').write_text(json.dumps(expected,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-Fbin','-quiet','-L','test.list','-o','test.bin','test.s'],cwd=o,check=True)
pos=normal.find(bytes.fromhex('d0ab001c2240'));pos=normal.find(bytes.fromhex('d0ab001c2240'),pos+6);assert pos>=0
normal[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');normal+=(o/'test.bin').read_bytes();normal+=b'\0'*((-len(normal))%4)
code=bytearray(base);code[20:24]=struct.pack('>I',len(normal)//4);code[28:32]=code[20:24];(o/'test.slave').write_bytes(code[:32]+normal+bytes.fromhex('000003f2'))
print('Built PAL timer guest tests:',len(expected),'cases')
