from pathlib import Path
import struct,subprocess,json,hashlib
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-b5v4-wear-test';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();assert hashlib.sha256(base).hexdigest()=='b8f0985e47a73b12f4822bf15960c3d6980f3484d261a5b009c163ca23a3630f'
prefix=(r/'tools/build_step5_position_test.py').read_text().split("prefix='''",1)[1].split("'''",1)[0]
cases=[]
def add(condition,rem,rate):
 bad=condition<0 or rate<0 or not 0<=rem<=4
 loss=rate;rr=rem
 if not bad:
  loss,rr=divmod(rate+rem,5)
  if loss>=condition:loss=condition;rr=0
 cases.append(dict(condition=condition,rem=rem,rate=rate,expected=[loss&0xffffffff,rr&0xffffffff,0xffffffff if bad else 0,condition&0xffffffff]))
 return condition-loss,rr
for condition in (0,1,2,10,0xff0000,0x7fffffff):
 for rem in range(5):
  for rate in (0,1,4,5,10,100,0x7fffffff):add(condition,rem,rate)
for condition,rem,rate in ((-1,0,5),(10,0,-1),(10,5,1),(10,255,1)):add(condition,rem,rate)
for rate in (1,3,17,100):
 condition=1000;rem=0
 for _ in range(10):condition,rem=add(condition,rem,rate)
asm=prefix
for i,c in enumerate(cases):
 asm+=f" lea state(pc),a0\n lea remainder(pc),a1\n move.l #${c['condition']&0xffffffff:08x},(a0)\n move.b #$a5,1(a1)\n move.b #{c['rem']},(a1)\n move.l #${c['rate']&0xffffffff:08x},d0\n bsr.w FF1Wear20Delta\n lea results+{i*16}(pc),a3\n move.l d0,(a3)+\n moveq #0,d2\n move.b (a1),d2\n move.l d2,(a3)+\n move.l d1,(a3)+\n move.l (a0),(a3)+\n cmpi.b #$a5,1(a1)\n beq.b .canary{i}\n move.l #-2,-8(a3)\n.canary{i}:\n"
asm+=' rts\n include "'+str(r.parent.parent/'Games/FerrariFormulaOne_Wear.s')+'"\ninstalled: dc.l 0\nstate: ds.l 1\nremainder: ds.w 1\nresults: ds.l '+str(len(cases)*4)+'\n'
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n')
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-DFF1_HELPERS_020=1','-Fbin','-quiet','-DFF1_PLAYER_HOOKS=1','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'wear integration cases')
