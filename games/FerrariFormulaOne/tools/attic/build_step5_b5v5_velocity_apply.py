from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b5v5-velocity-apply-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
cases=[]
def add(vector,rems,response,alias=0):
 response=vector[:] if alias else response
 output=[];rema=[];overflow=False
 for value,rem,rate in zip(vector,rems,response):
  total=rate+rem;q=(abs(total)//5)*(1 if total>=0 else -1)
  overflow|=not -2**31<=total<2**31 or not -2**31<=value+q<2**31
  output.append(value+q);rema.append(total-q*5)
 if overflow:output=vector[:];rema=rems[:]
 expected=[output[0]&0xffffffff,output[1]&0xffffffff,((rema[0]&65535)<<16)|(rema[1]&65535),0xffffffff if overflow else 0]
 cases.append(dict(vector=vector[:],remainders=rems[:],response=response[:],alias=alias,expected=expected))
 return output,rema
for response in ([65536,3],[-65536,-3],[1,-1],[1234567,-7654321]):
 v=[0,0];rem=[0,0]
 for _ in range(5):v,rem=add(v,rem,response)
 for _ in range(5):v,rem=add(v,rem,[-x for x in response])
for axis in (0,1):
 for value,rem,rate in ((2**31-1,0,5),(-2**31,0,-5),(0,4,2**31-1),(0,-4,-2**31),(0,4,0),(0,-4,0)):
  v=[100,-100];rr=[1,-1];rates=[1,-1];v[axis]=value;rr[axis]=rem;rates[axis]=rate;add(v,rr,rates)
for vector in ([1234567,-7654321],[2**31-1,1],[1,-2**31],[0,0]):add(vector,[3,-3],[0,0],1)
asm=prefix
for i,c in enumerate(cases):
 asm+=' lea state(pc),a0\n lea remainders(pc),a1\n lea response(pc),a2\n'
 for axis in range(2):
  asm+=f" move.l #${c['vector'][axis]&0xffffffff:08x},{axis*4}(a0)\n move.w #{c['remainders'][axis]},{axis*2}(a1)\n move.l #${c['response'][axis]&0xffffffff:08x},{axis*4}(a2)\n"
 if c['alias']:asm+=' move.l a0,a2\n'
 asm+=f' bsr.w FF1VelocityApply20\n lea results+{i*16}(pc),a3\n move.l (a0),(a3)+\n move.l 4(a0),(a3)+\n move.l (a1),(a3)+\n move.l d1,(a3)\n'
asm+=' rts\n'
for name in ('Math','Step','Velocity'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+name+'.s'))+'"\n'
asm+='installed: dc.l 0\nstate: ds.l 2\nremainders: ds.w 2\nresponse: ds.l 2\nresults: ds.l '+str(len(cases)*4)+'\n'
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_HELPERS_020=1','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'continuous response cases')
