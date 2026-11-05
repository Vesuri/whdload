from pathlib import Path
import json,struct,subprocess,hashlib,math,itertools
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b5v4-wide-extended-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
cases=[]
for root in sorted(set(range(0,65536,257)) | set(range(1019,1030)) | {7039,8928,32767,32768,65534,65535} | {max(0,2**k+d) for k in range(16) for d in (-1,0,1)}):
 for n in (root*root-1,root*root,root*root+1):
  if 0<=n<=0xffffffff:cases.append(dict(op=0,a=n,b=0,c=0,expected=[math.isqrt(n),0]))
cases.append(dict(op=0,a=0xffffffff,b=0,c=0,expected=[65535,0]))
for component,limit,mag in itertools.product((-32768,-8928,-1024,-1,0,1,1024,8928,32767),(0,1,26,500,32767,-1),(0,1,38,1023,8928,32767,65535,65536)):
 prod=component*limit;q=(abs(prod)//mag)*(1 if prod>=0 else -1) if mag else 0
 bad=limit<0 or not 1<=mag<=65535 or not -32768<=q<=32767
 cases.append(dict(op=1,a=component&0xffffffff,b=limit&0xffffffff,c=mag,expected=[(component if bad else q)&0xffffffff,0xffffffff if bad else 0]))
for n in range(1024):cases.append(dict(op=0,a=n,b=0,c=0,expected=[math.isqrt(n),0]))
# Batch guest data so the 68000 fixture and Amiga memory stay bounded.
for batch_no,start in enumerate(range(0,len(cases),6000)):
 batch=cases[start:start+6000];name=f'b{batch_no:02d}'
 asm=prefix+''' lea (vectors,pc),a3
 lea results(pc),a4
 move.w #COUNT-1,d7
.loop:
 move.l 4(a3),d0
 tst.l (a3)
 bne.b .limit
 bsr.w FF1SquareRootU32
 moveq #0,d1
 bra.b .save
.limit:
 move.l 8(a3),d1
 move.l 12(a3),d2
 bsr.w FF1VelocityLimit020
.save:
 move.l d0,(a4)+
 move.l d1,(a4)+
 adda.w #16,a3
 dbra d7,.loop
 rts
'''.replace('COUNT',str(len(batch)))
 for module in ('Math','Step','Sqrt','Velocity'):asm+=' include "'+str(r.parent.parent/('Games/FerrariFormulaOne_'+module+'.s'))+'"\n'
 asm+='installed: dc.l 0\nresults: ds.l '+str(len(batch)*2)+'\nvectors: incbin "'+name+'-vectors.bin"\n'
 (o/(name+'-vectors.bin')).write_bytes(b''.join(struct.pack('>4I',c['op'],c['a'],c['b'],c['c']) for c in batch));(o/(name+'.json')).write_text(json.dumps(batch)+'\n');(o/(name+'.s')).write_text(asm)
 subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_HELPERS_020=1','-Fbin','-quiet','-L',name+'.list','-o',name+'.bin',name+'.s'],cwd=o,check=True)
 code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6);code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/(name+'.bin')).read_bytes();code+=b'\0'*((-len(code))%4)
 header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/(name+'.slave')).write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'wide tyre arithmetic cases in',batch_no+1,'batches')
