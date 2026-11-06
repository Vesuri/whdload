"""Run actual low-page native helpers against original FPSP opcodes in guest."""
import os,sys,json,struct,subprocess,random,math
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
import csv,collections
ops=[('tan',7,0,0x1c0f),('sin',7,0,0x1c0e),('cos',7,0,0x1c1d),('atan2',1,5,0x068a),('atan',7,0,0x1c0a),('asin',7,0,0x1c0c)]
keys={n:0x1fc+6*i for i,(n,_,_,_) in enumerate(ops)}
meta={'sites':[dict(key=n,original=f'f200{op:04x}',dest=d) for n,_,d,op in ops]}
def ext(v):
 if not v:return struct.pack('>III',0x80000000 if math.copysign(1,v)<0 else 0,0,0)
 m,e=math.frexp(abs(v));sig=int(m*2**64);return struct.pack('>IQ',((e-1+16383)|(0x8000 if v<0 else 0))<<16,sig)
observed=[]
for row in csv.reader((ROOT/'tmp/step9/baseline-operands/profile.csv').open()):
 if row[0]=='math' and row[3]=='0':observed.append(struct.pack('>III',*map(int,row[4:7])))
vals=[0.,-0.,1e-10,-1e-10,.1,-.1,.5,-.5,.9,-.9,1.,-1.,1-2**-52,-1+2**-52,math.pi/4,-math.pi/4,math.pi/2,-math.pi/2,math.pi,100.,-100.,1000.,-1000.,1e6,-1e6,2**20,-2**20]
r=random.Random(9);vals += [r.uniform(-1,1) for _ in range(40)]
values=list(dict.fromkeys(observed+[ext(v) for v in vals]))
records=[];asm=[' mc68040','start:']
for k,slot in keys.items():
 site=next(s for s in meta['sites'] if s['key']==k);op=site['original'];label=k
 asm += [f' lea inputs(pc),a0',f' move.w #{len(values)-1},d7',label+':',' fmove.l #0,fpcr',' fmovem.x (a0),fp0-fp7'] # inputs repeat same value eight times
 asm += [f' jsr ${slot:x}.w',' fmovem.x fp0-fp7,(a2)',' lea 96(a2),a2',' fmove.l fpsr,(a2)+',' fmove.l fpcr,(a2)+',' fmovem.x (a0),fp0-fp7',f' dc.l ${op}',' fmovem.x fp0-fp7,(a2)',' lea 96(a2),a2',' fmove.l fpsr,(a2)+',' fmove.l fpcr,(a2)+',' lea 96(a0),a0',f' dbf d7,{label}']
 records += [dict(key=k,value=x.hex(),dest=site['dest']) for x in values]
asm=[' mc68040',' move.l #'+str(len(records)*208)+',d0',' move.l #$10005,d1',' move.l 4.w,a6',' jsr -198(a6)',' move.l d0,a2',' move.l d0,a3']+asm[1:]
asm+=['finished:',' bra.s finished','inputs:']
for v in values:
 for _ in range(8):asm+=[' dc.l '+','.join('$'+v[i:i+4].hex() for i in range(0,12,4))]
tmp=ROOT/'tmp/step9/test-math.s';tmp.write_text('\n'.join(asm)+'\n')
subprocess.run(['bash','-c','. tools/env.sh; "$VASM" -Fbin -o tmp/step9/test-math.bin tmp/step9/test-math.s'],check=True,stdout=subprocess.DEVNULL)
blob=(ROOT/'tmp/step9/test-math.bin').read_bytes();end=len(blob)-len(values)*96-2

def capture(cmd,dump,bases,hs,out):
 b=bases[0];code=b+0x6000;output=b+0x10000
 cmd('delete breakpoints');cmd('monitor tfxreg 16 2700')
 for off in range(0,len(blob),32):cmd(f'monitor tfxmem {code+off:x} {blob[off:off+32].hex()}')
 cmd(f'monitor tfxreg 10 {output:x}');cmd(f'monitor tfxreg 17 {code:x}');cmd(f'break *{code+end:#x}')
 reply=cmd('continue');assert f'0x{code+end:08x}' in reply,reply
 import re
 output=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $a3'))[1],16);assert 0x40000000<=output<0x42000000
 cmd(f'monitor tfxsync {output:x} {len(records)*208}')
 data=dump('results.bin',output,len(records)*208)
 results=[]
 for i,rec in enumerate(records):
  a=data[i*208:i*208+104];b=data[i*208+104:i*208+208];dst=rec['dest'];offset=dst*12
  # Extended memory padding is unspecified, compare exponent and significand only.
  clean=lambda x:x[:2]+x[4:12]
  def number(x):
   w,hi,lo=struct.unpack('>III',x);e=(w>>16)&32767
   if e==32767:return float('nan')
   return (-1 if w>>31 else 1)*math.ldexp((hi*2**32+lo)/2**63,e-16383) if e else (-0. if w>>31 else 0.)
  av=number(a[offset:offset+12]);bv=number(b[offset:offset+12]);error=abs(av-bv)
  same=(math.isnan(av) and math.isnan(bv)) or error<=2e-15*max(1,abs(bv))
  preserved=all(clean(a[j*12:(j+1)*12])==clean(b[j*12:(j+1)*12]) for j in range(8) if j!=dst)
  same=same and preserved
  results.append(dict(rec,error=error,native_value=av,fpsp_value=bv,preserved=preserved,equal=same,native=a.hex(),fpsp=b.hex(),fpsr_equal=a[96:100]==b[96:100],fpcr_equal=a[100:104]==b[100:104]))
 (out/'results.json').write_text(json.dumps(results,indent=2));print('cases',len(results),'values equal',sum(x['equal'] for x in results),'FPSR equal',sum(x['fpsr_equal'] for x in results),flush=True)
 # Full-domain truth is checked separately against the Decimal oracle.
 assert all(x['preserved'] and x['fpcr_equal'] for x in results)
v=dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040',out,Path(os.environ.get('TEST_SEED',str(out)+'-seed')),capture,v)
