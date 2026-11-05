from pathlib import Path
import struct,subprocess,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b6-trig-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();normal=base[32:-4];size=len(normal)
scales=(0,1,-1,2,-2,1000,-1000,32767,-32768,12345)
cases=[(0xabcd0000|a,0x76540000|(b&65535)) for a in range(1024) for b in scales]
cases += [(0xabcd0000|(alias*1024+a),0x76540000|(b&65535)) for alias in range(64) for a in (0,1,511,512,1023) for b in (32767,-32768)]
(o/'cases.bin').write_bytes(b''.join(struct.pack('>II',*v) for v in cases))
start=(r/'tmp/build/step5-b6-track-test/track.s').read_text().split('tests:')[0]
test='''tests:
 lea cases(pc),a2
 move.w #COUNT-1,d6
.case:
 moveq #0,d7
.flags:
 move.l 4(a2),-(sp)
 move.l (a2),-(sp)
 move.w d7,ccr
 jsr $24fe0
 move.w ccr,d4
 move.l d0,a3
 move.l a0,a4
 move.w d7,ccr
 bsr.w FF1NativeSine
 move.w ccr,d5
 bsr.w compare
 addq.l #8,sp
 tst.l error
 bne.b .done
 move.l 4(a2),-(sp)
 move.l (a2),-(sp)
 move.w d7,ccr
 jsr $25000
 move.w ccr,d4
 move.l d0,a3
 move.l a0,a4
 move.w d7,ccr
 bsr.w FF1NativeCosine
 move.w ccr,d5
 bsr.w compare
 addq.l #8,sp
 tst.l error
 bne.b .done
 tst.w d7
 bne.b .next
 moveq #31,d7
 bra.b .flags
.next:
 addq.l #8,a2
 dbra d6,.case
.done: rts
compare:
 cmp.l a3,d0
 bne.b .bad
 cmpa.l a4,a0
 bne.b .bad
 eor.w d4,d5
 andi.w #31,d5
 bne.b .bad
 lea checked(pc),a1
 addq.l #1,(a1)
 rts
.bad:
 lea error(pc),a1
 move.l #1,(a1)
 lea failed_case(pc),a1
 move.l a2,(a1)+
 move.l d0,(a1)+
 move.l a3,(a1)+
 move.l a0,(a1)+
 move.l a4,(a1)+
 rts
'''.replace('COUNT',str(len(cases)))
module=(r.parents[1]/'Games/FerrariFormulaOne_NativeExact.s').read_text();helper='FF1NativeSine:'+module.split('FF1NativeSine:')[1].split('FF1TrigSignature:')[0]
s=start+test+helper+'\ninstalled: dc.l 0\nchecked: dc.l 0\nerror: dc.l 0\nfailed_case: ds.l 5\noutputs: ds.b 12\ncases: incbin "cases.bin"\n'
(o/'trig.s').write_text(s)
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L','trig.list','-o','trig.bin','trig.s'],cwd=o,check=True)
code=bytearray(normal);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'trig.bin').read_bytes();code+=b'\0'*((-len(code))%4)
h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'trig.slave').write_bytes(h+code+bytes.fromhex('000003f2'))
(o/'expected.json').write_text(json.dumps(dict(comparisons=len(cases)*4,scope='Both tables; all 1024 angles, signed scale boundaries, full-word angle aliases and XNZVC'))+'\n')
s=(r/'tools/test_step5_b6_track.py').read_text().replace('step5-b6-track-test','step5-b6-trig-test').replace('b6-track-oracle','b6-trig-oracle').replace("'track.list'","'trig.list'").replace("'track.slave'","'trig.slave'")
(r/'tools/test_step5_b6_trig.py').write_text(s);print('Built',len(cases)*4,'full-result/flags/pointer trig comparisons')
