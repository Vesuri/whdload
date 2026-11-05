from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b5v3-speed-rate-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
cases=[]
def add(q,rem,proposal):
 total=(proposal-(q>>16))*65536+rem
 delta=(abs(total)//5)*(1 if total>=0 else -1);rr=total-delta*5
 nq=q+delta
 bad=not 0<=q<=500*65536 or not -4<=rem<=4 or not -2**31<=delta<2**31 or not -2**31<=nq<2**31
 if bad:nq,rr=q,rem
 elif nq*5+rr<0:nq,rr=0,0
 elif nq*5+rr>500*65536*5:nq,rr=500*65536,0
 cases.append(dict(q=q,rem=rem,proposal=proposal,expected=[nq&0xffffffff,rr&0xffffffff,0xffffffff if bad else 0,0]))
 return nq,rr
for q in (0,1,3*65536+32768,492*65536,500*65536):
 for rem in (-4,0,4):
  for proposal in (-32768,-182,0,1,4,500,32767):add(q,rem,proposal)
for q,rem,proposal in ((-1,0,1),(500*65536+1,0,1),(0,-5,1),(0,5,1),(0,0,2**31-1)):
 add(q,rem,proposal)
for start,increment in ((200,1),(200,-1),(492,-674),(0,3)):
 q=start*65536;rem=0
 for _ in range(5):q,rem=add(q,rem,(q>>16)+increment)
asm=prefix
for i,c in enumerate(cases):
 asm+=' lea state(pc),a0\n'
 asm+=f" move.l #${c['q']&0xffffffff:08x},(a0)\n move.w #{c['rem']},4(a0)\n move.l #${c['proposal']&0xffffffff:08x},d0\n"
 asm+=f' bsr.w FF1SpeedRate20\n lea results+{i*16}(pc),a3\n move.l (a0),(a3)+\n move.w 4(a0),d0\n ext.l d0\n move.l d0,(a3)+\n move.l d1,(a3)+\n clr.l (a3)\n'
asm+=' rts\n'
asm+=' include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Speed.s')+'"\n'
asm+=' include \"'+str(r.parent.parent/'Games/FerrariFormulaOne_Sqrt.s')+'\"\n'
asm+='installed: dc.l 0\nstate: ds.b 6\nresults: ds.l '+str(len(cases)*4)+'\n'
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_HELPERS_020=1','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'scalar speed cases')
