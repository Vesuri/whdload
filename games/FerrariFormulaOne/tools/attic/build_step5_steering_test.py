from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-steering-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
import random
cases=[]
def w(x):return ((x+32768)&65535)-32768
def add(history,cursor,last,held,raw,tick,op=0):
 initial=struct.pack('>5hHIh',*history,cursor,last,held);h=history[:];ix=cursor;gap=(tick-last)&0xffffffff;filtered=raw;delayed=0;status=0
 if op:h=[raw]*5;ix=0;last=tick;held=raw
 elif cursor>4 or gap==0 or gap>=2**31:status=0xffffffff
 else:
  if gap>=5:h=[held]*5;ix=0
  else:
   for _ in range(gap-1):h[ix]=held;ix=(ix+1)%5
  delayed=h[ix];h[ix]=raw;ix=(ix+1)%5;last=tick;held=raw;filtered=w(raw+delayed)//2
 expected=struct.pack('>5hHIhHiiI',*h,ix,last,held,0,filtered,delayed,status)
 cases.append(dict(initial=initial.hex(),raw=raw,tick=tick,op=op,expected=list(struct.unpack('>8I',expected))))
for cursor in range(5):
 for gap in (0,1,2,3,4,5,6,100,0xffffffff):add([-32768,-7,0,18,32767],cursor,100,27,-23,(100+gap)&0xffffffff)
for raw in (-32768,-1,0,1,32767):
 for held in (-32768,-1,0,1,32767):add([held]*5,0,0,held,raw,1)
for last,tick in ((0xffffffff,0),(0xfffffffc,2),(0x7fffffff,0x80000000),(0x7ffffffc,0x80000002),(0,0x80000000)):
 add([1,2,3,4,5],2,last,5,19,tick)
for cursor in (5,65535):add([1,2,3,4,5],cursor,0,5,19,1)
for raw in (-32768,0,32767):add([1,2,3,4,5],4,99,7,raw,123,1)
asm=prefix+' lea inputs(pc),a4\n lea results(pc),a3\n move.w #'+str(len(cases)-1)+',d7\n.loop:\n lea state(pc),a0\n'
for off in range(0,16,4):asm+=f' move.l (a4)+,{off}(a0)\n'
asm+=' move.w (a4)+,16(a0)\n move.w (a4)+,d0\n ext.l d0\n move.l (a4)+,d3\n move.l (a4)+,d6\n moveq #0,d2\n moveq #0,d1\n tst.l d6\n bne.b .reset\n bsr.w FF1SteeringSample20\n bra.b .record\n.reset:\n bsr.w FF1SteeringReset\n.record:\n'
for off in range(0,16,4):asm+=f' move.l {off}(a0),(a3)+\n'
asm+=' move.w 16(a0),(a3)+\n clr.w (a3)+\n move.l d0,(a3)+\n move.l d2,(a3)+\n move.l d1,(a3)+\n dbra d7,.loop\n rts\n'
asm+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Steering.s')+'"\ninstalled: dc.l 0\nstate: ds.b 18\ninputs:\n'
for c in cases:
 data=bytes.fromhex(c['initial'])+struct.pack('>hII',c['raw'],c['tick'],c['op']);asm+=' dc.b '+','.join('$'+format(v,'02x') for v in data)+'\n'
asm+='results: ds.l '+str(len(cases)*8)+'\n'
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'steering history cases')
