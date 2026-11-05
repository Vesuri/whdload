from pathlib import Path
import subprocess,struct,json,itertools
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b8-ownership-test';o.mkdir(exist_ok=True);base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0].replace('move.w sr','move.w ccr')
def w(v):return ((v+32768)%65536)-32768
cases=[]
for steer,speed in [(0,0),(-32768,500),(32767,500),(-513,400),(512,330),(-1,1),(1,-1),(1024,32767)]:
 for segment,flag,mode in itertools.product((19,20,21,29,30,31),(0,1,2),(0,1)):
  inside=20<segment<30;newflag=1 if inside and not flag else flag if inside else 0
  msg=(1 if inside else 2) if mode and newflag!=flag else 0
  right=w(w((steer>>5)+32)*speed)>>4;left=w(w(32-(steer>>5))*speed)>>4
  yaw=(segment-20)*128;view=int(256<(yaw&1023)<768)
  cases.append(dict(inputs=[steer,speed,segment,flag,mode,yaw],expected=[right,left]+[newflag]*8+[msg,view]))
(o/'inputs.bin').write_bytes(b''.join(struct.pack('>6h',*c['inputs']) for c in cases));(o/'expected.json').write_text(json.dumps(cases,indent=2))
s=prefix+f''' lea inputs(pc),a4
 lea results(pc),a5
 move.w #{len(cases)-1},d6
 move.w #20,$1c1e2
 move.w #30,$1c1e4
.loop:
 move.w (a4),$1c6a2
 move.w 2(a4),$2275a
 move.w 8(a4),$1c1c2
 move.w 10(a4),$6a67a
 clr.w $66f96
 lea B8PitMessage(pc),a0
 clr.w (a0)
 lea $6a60a,a0
 lea $d0dc,a1
 moveq #7,d0
.seed:
 move.w 4(a4),(a0)+
 move.b 7(a4),(a1)+
 dbra d0,.seed
 bsr.w B8NativePresentationTick
 bsr.w B8ViewTick
 move.w $66c88,(a5)+
 move.w $66c8a,(a5)+
 lea $d0dc,a0
 move.l (a0)+,(a5)+
 move.l (a0)+,(a5)+
 move.w B8PitMessage(pc),(a5)+
 move.w $66c7c,(a5)+
 lea 12(a4),a4
 dbra d6,.loop
 rts
 include "FerrariFormulaOne_RenderOwnership.s"
installed: dc.l 0
inputs: incbin "inputs.bin"
results: ds.b {len(cases)*16}
'''
(o/'ownership.s').write_text(s);subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_RENDER_POSES=1','-Fbin','-quiet','-I'+str(r.parents[1]/'Games'),'-L','ownership.list','-o','ownership.bin','ownership.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);size=len(code);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',size-pos-2)+bytes.fromhex('4e71');code+=(o/'ownership.bin').read_bytes();code+=b'\0'*((-len(code))%4);h=bytearray(base[:32]);h[20:24]=struct.pack('>I',len(code)//4);h[28:32]=h[20:24];(o/'ownership.slave').write_bytes(h+code+bytes.fromhex('000003f2'));print(len(cases),'ownership cases')
p=r/'tools/test_step5_b8_history.py';t=p.read_text().replace('step5-b8-history-test','step5-b8-ownership-test').replace('history.list','ownership.list').replace('history.slave','ownership.slave').replace('b8-history-','b8-ownership-').replace("'>8h'","'>hh8Bhh'").replace('want=e\n',"want=e['expected']\n");(r/'tools/test_step5_b8_ownership.py').write_text(t)
