from pathlib import Path
import struct,subprocess,hashlib,json
r=Path(__file__).resolve().parents[1];o=r/'tmp/build/step5-fuel-transition';o.mkdir(parents=True,exist_ok=True)
base=(r/'tmp/build/release/FerrariFormulaOne.slave').read_bytes();m=(r/'tmp/step4/a1200-c1/anchor.bin').read_bytes()
asm=(r/'tmp/build/step5-fuel-fine/fine.s').read_text().replace(' bsr.w install_fuel\n',' bsr.w install_fuel\n bsr.w fuel_native_tests\n bra.l fuel_test_stop\n',1)
body,buffers=asm.split('velocity_records: ds.b 64000',1)
extra='fuel_native_tests:\n'
for a in (0x6d16a,0x64aec,0x68824,0x6c6a8,0x6694a,0x6d24a):extra+=f' cmpi.w #${m[a:a+2].hex()},${a:x}\n bne.w velocity_fault\n move.w #$4e75,${a:x}\n'
extra+=' lea (start.l,pc),a2\n suba.l #5440,a2\n move.l $1180(a2),a2\n jsr $20(a2)\n'
cases=[]
def emit(mode,car,before,rem,rate,site,kind):
 global extra
 addr=0x22376+4*car;delta=rate;newrem=rem;after=before
 if kind=='consume':
  if mode==8:
   delta,newrem=divmod(rate+rem,5)
   if delta>=before:delta=before;newrem=0
  after=(before-delta)&0xffffffff
 elif kind=='absolute':after=rate;newrem=0 if mode==8 else rem
 elif kind=='refill':after=rate*10000;delta=after;newrem=0 if mode==8 else rem
 else:after=0;newrem=0 if mode==8 else rem
 i=len(cases);expected=[after,newrem,delta&0xffffffff,0];cases.append(dict(kind=kind,site=hex(site),mode=mode,car=car,before=before,rem=rem,rate=rate,expected=expected))
 extra+=f' lea modeval(pc),a0\n move.w #{mode},(a0)\n lea fuel_samples(pc),a0\n clr.l (a0)\n lea fuel_remainders(pc),a1\n move.w #{rem},{car*2}(a1)\n move.l #{before},${addr:x}\n move.w #{car},$32fbc\n lea fuel_test_local+4(pc),a6\n move.l #{rate},d0\n'
 extra+=f' movea.l #{car*4 if kind=="clear" else addr},a0\n jsr ${site:x}\n lea (fuel_test_results+{i*16}.l,pc),a3\n move.l ${addr:x},(a3)+\n moveq #0,d1\n lea fuel_remainders(pc),a1\n move.w {car*2}(a1),d1\n move.l d1,(a3)+\n move.l d0,(a3)+\n move.l error(pc),(a3)+\n'
for mode in (7,8):
 for car in range(8):
  for before,rem,rate in ((0,4,1),(1,4,1),(1,0,100),(10,3,2),(1000,0,17),(1000,4,17),(0x7fffffff,4,0x7fffffff)):
   emit(mode,car,before,rem,rate,0x6d164,'consume')
  for site in (0x6881e,0x6c6a2):
   for rate in (0,1,999):emit(mode,car,12345,4,rate,site,'refill')
  for site in (0x66942,0x6d242):emit(mode,car,12345,4,77,site,'clear')
 for rate in (0,1,100000):emit(mode,0,12345,4,rate,0x64ae6,'absolute')
extra+=' lea fuel_test_complete(pc),a0\n move.l #1,(a0)\n rts\nfuel_test_stop:\n bra.b fuel_test_stop\nfuel_test_complete: dc.l 0\nfuel_test_local: ds.l 2\n'
asm=body+extra+'velocity_records: ds.b 64000'+buffers+f'fuel_test_results: ds.b {len(cases)*16}\n'
(o/'fine.s').write_text(asm);(o/'fine.json').write_text(json.dumps(cases,indent=2)+'\n');(o/'original_div.bin').write_bytes((r/'tmp/build/step5-fuel-fine/original_div.bin').read_bytes())
subprocess.run([str(Path.home()/'.local/vasmm68k_mot'),'-m68020','-Fbin','-quiet','-L','fine.list','-o','fine.bin','fine.s'],cwd=o,check=True)
code=bytearray(base[32:-4]);pos=code.find(bytes.fromhex('d0ab001c2240'));pos=code.find(bytes.fromhex('d0ab001c2240'),pos+6)
code[pos:pos+6]=bytes.fromhex('6100')+struct.pack('>h',len(code)-pos-2)+bytes.fromhex('4e71');code+=(o/'fine.bin').read_bytes();code+=b'\0'*((-len(code))%4)
header=bytearray(base[:32]);header[20:24]=struct.pack('>I',len(code)//4);header[28:32]=header[20:24];(o/'fine.slave').write_bytes(header+code+bytes.fromhex('000003f2'))
print(len(cases),'native fuel transition cases')
