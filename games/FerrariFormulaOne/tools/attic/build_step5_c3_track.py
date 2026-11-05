from pathlib import Path
import struct,subprocess,re,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-c3-track-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];size=len(normal)
cases=[(836,i,m) for m in (0,1) for i in range(836)]
cases += [(count,seg,mode) for count in (0,1,11,12,13,64,835,836,32766,32767) for seg in (-1,0,1,11) for mode in (0,1)]
cases += [(count,seg,0) for count in (12,13,64,835,836) for seg in (count-2,count-1,count,count+1)]
(o/'cases.bin').write_bytes(b''.join(struct.pack('>HhH',*v) for v in cases))
s='''start:
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
done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
barrier:
 jsr $2a130
 movem.l d0-a6,-(sp)
 move.w sr,-(sp)
 lea ticks(pc),a0
 addq.l #1,(a0)
 cmpi.l #100,(a0)
 bne.b .done
 bsr.w tests
.done:
 move.w (sp)+,ccr
 movem.l (sp)+,d0-a6
 rts
ticks: dc.l 0
tests:
 move.w $1ed8a,-(sp)
 move.w $2268c,-(sp)
 lea cases(pc),a2
 move.w #COUNT-1,d6
.loop:
 move.w (a2),$2268c
 move.w 4(a2),$1ed8a
 move.w 2(a2),d0
 ext.l d0
 move.l d0,-(sp)
 jsr $6977a
 addq.l #4,sp
 move.l d0,d7
 move.w 2(a2),d0
 ext.l d0
 move.l d0,-(sp)
 bsr.w FF1NativeLookahead
 addq.l #4,sp
 cmp.l d7,d0
 bne.b .failed
 lea checked(pc),a0
 addq.l #1,(a0)
 addq.l #6,a2
 dbra d6,.loop
 bra.b .done
.failed:
 lea error(pc),a0
 move.l #1,(a0)
 lea failed_case(pc),a0
 move.l a2,(a0)+
 move.l d0,(a0)+
 move.l d7,(a0)+
.done:
 move.w (sp)+,$2268c
 move.w (sp)+,$1ed8a
 rts
installed: dc.l 0
checked: dc.l 0
error: dc.l 0
failed_case: ds.l 5
outputs: ds.b 12
cases: incbin "cases.bin"
'''.replace('COUNT',str(len(cases)))
module=(r.parents[1]/'Games/FerrariFormulaOne_NativeExact.s').read_text();s+='FF1NativeLookahead:'+module.split('FF1NativeLookahead:')[1].split('FF1TrackSignature:')[0]
(o/'track.s').write_text(s)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68000','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','track.list','-o','track.bin','track.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'track.bin').read_bytes();code+=b'\0'*((-len(code))%4)
h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'track.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
(o/'expected.json').write_text(json.dumps(dict(comparisons=len(cases),scope='Native lookahead value oracle: both modes, every demo segment, count/segment guards and wrapping boundaries'))+'\n')
# Reuse the strict startup guest-oracle runner, both CPU profiles.
s=(r/'tools/test_step5_div.py').read_text().replace('step5-div-test','step5-c3-track-test').replace("(('a500',0),('a1200',0),('a1200',1))","(('a500',1),)").replace("if profile=='a1200':","if profile.startswith('a1200'):").replace("'div-oracle-'","'c3-track-oracle-'").replace("('div'+str(mode)+'.list')","'track.list'").replace("('div'+str(mode)+'.slave')","'track.slave'")
s=s.replace("cmd('break *0x65174');","cmd('break *0x65606');cmd('ignore $bpnum 99');")
(r/'tools/test_step5_c3_track.py').write_text(s)
print('Built',len(cases),'native lookahead cases')
