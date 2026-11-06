"""Native full-array, register and FP-state comparisons for Project."""
import os,sys,struct,json,random,subprocess,re
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
r=random.Random(204013);cases=[]
values=[-2147483648,-2147483647,-1073741824,-557057,-557056,-557055,-1,0,1,557038,557039,557040,2147483647]
for i in range(160):
 n=[1,2,4,8][i%4];z=[16,17,18,32767,-1,0,500][i%7]
 pts=[]
 for j in range(n):
  x=values[(i+j)%len(values)] if i<100 else r.randint(-2147483648,2147483647)
  y=values[(i*3+j)%len(values)] if i<100 else r.randint(-2147483648,2147483647)
  depth=z if j==0 or i%3 else 16
  pts.append([x,y,(depth<<16)&0xffffffff])
 cases.append(dict(points=pts,shift=[0,1,5,16,31][i%5],fpcr=[0,0x10,0x80,0x40][i%4]))
import csv
observed=[]
for row in csv.reader((ROOT/'tmp/opt20/project-observer-on/profile.csv').open()):
 if row[0]=='math' and row[2]==str(0x55e6c):
  observed.append(tuple(map(int,row[4:7])))
for x,y,z in observed[::10000]:
 signed=lambda v:v-2**32 if v>=2**31 else v
 pt=[signed(x),signed(y),(z&65535)<<16]
 cases.append(dict(points=[pt,pt],shift=0,fpcr=0))
for i in range(32):
 cases.append(dict(points=[[r.randint(-2**31,2**31-1),r.randint(-2**31,2**31-1),r.getrandbits(32)] for _ in range(4)],shift=i,fpcr=0,translation=[r.getrandbits(32) for _ in range(3)]))
def capture(cmd,dump,bases,hs,out):
 b=bases[0];entry=b+0x55e32;raw=dump('project-entry.bin',entry,6);assert raw[:2]==bytes.fromhex('4ef9');native=int.from_bytes(raw[2:],'big')
 original=hs[0]['bytes'][0x55e32:0x55e38];cmd(f'monitor tfxmem {entry:x} {original.hex()}')
 code=b+0x8000;par=b+0x55bf4;target=par+0xf2;stride=512
 a=[' mc68040',f' org ${code:x}',' move.l #400000,d0',' move.l #$10001,d1',' move.l 4.w,a6',' jsr -198(a6)',' move.l d0,mem']
 for i,c in enumerate(cases):
  n=len(c['points'])
  for side in range(2):
   a += [' move.l mem(pc),a1']
   for j,pt in enumerate(c['points']):
    for k in range(9):
     val=pt[k-5] if 5<=k<8 else 0xa55a6996
     a += [f' move.l #${val&0xffffffff:x},{j*36+k*4}(a1)']
   for o,val in [(0,c.get("translation",[0,0,0])[0]),(4,c.get("translation",[0,0,0])[1]),(8,c.get("translation",[0,0,0])[2]),(0x10a,0x12345678),(0x10e,0x34567890),(0x112,0x789abcde),(0xf2,0),(0xf6,0),(0xfa,0)]:a += [f' move.l #${val:x},${par+o:x}']
   a += [f' move.w #{c["shift"]},${par+12:x}',f' move.w #{c["shift"]},${par+14:x}',f' move.w #160,${par+16:x}',f' move.w #100,${par+18:x}']
   a += [' fmove.l #0,fpcr',' fmove.s #1.25,fp0',f' fmove.l #${c["fpcr"]:x},fpcr',' fmove.l #$104,fpsr',' fmove.l #$12345678,fpiar',' move.l #$123456,a0',f' move.l #{n},d7',f' jsr ${entry if side==0 else native:x}']
   # MOVEM absolute stores preserve all tested GPRs and CCR.
   a += [f' movem.l d0-d7/a0-a6,regs', ' move.w ccr,flags',' fmovem.l fpcr/fpsr/fpiar,control',' fmovem.x fp0-fp7,fpregs',' move.l mem(pc),a0',f' lea {4096+(i*2+side)*stride}(a0),a1']
   a += [f' move.w #{n*9-1},d7',f'copy{i}_{side}:',' move.l (a0)+,(a1)+',f' dbf d7,copy{i}_{side}']
   a += [' lea regs(pc),a0',' moveq #14,d7',f'regs{i}_{side}:',' move.l (a0)+,(a1)+',f' dbf d7,regs{i}_{side}',' move.w flags(pc),(a1)+',' lea control(pc),a0',' moveq #26,d7',f'fp{i}_{side}:',' move.l (a0)+,(a1)+',f' dbf d7,fp{i}_{side}']
   a += [f' move.l ${target+o:x},(a1)+' for o in [0,4,8]]
 a+=['finished:',' bra.s finished','mem: dc.l 0','regs: ds.l 15','flags: dc.w 0','control: ds.l 3','fpregs: ds.l 24']
 src=out/'fixture.s';src.write_text('\n'.join(a)+'\n');bin=out/'fixture.bin';lst=out/'fixture.lst'
 subprocess.run(['bash','-c','. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"','fixture',str(src),str(bin),str(lst)],check=True)
 blob=bin.read_bytes();assert len(blob)<0x4d000, len(blob)
 labels={n:int(re.search(r'^'+n+r'\s+A:([0-9A-Fa-f]+)',lst.read_text(),re.M)[1],16) for n in ['mem','finished']}
 cmd('delete breakpoints');cmd('monitor tfxreg 16 2700')
 for off in range(0,len(blob),32):cmd(f'monitor tfxmem {code+off:x} {blob[off:off+32].hex()}')
 cmd(f'monitor tfxreg 17 {code:x}');cmd(f'break *{labels["finished"]:#x}');reply=cmd('continue');assert f'0x{labels["finished"]:08x}' in reply,reply
 cmd(f'monitor tfxsync {labels["mem"]:x} 4');mem=int.from_bytes(dump('mem.bin',labels['mem'],4),'big')
 cmd(f'monitor tfxsync {mem+4096:x} {len(cases)*2*stride}');data=dump('results.bin',mem+4096,len(cases)*2*stride)
 results=[]
 for i,c in enumerate(cases):
  n=len(c['points']);size=n*36+60+2+108+12;x=data[i*2*stride:i*2*stride+size];y=data[(i*2+1)*stride:(i*2+1)*stride+size]
  # Extended memory padding words are unspecified.
  skip={n*36+60+2+12+k*12+j for k in range(8) for j in [2,3]}
  diff=[j for j in range(size) if x[j]!=y[j] and j not in skip]
  results.append(dict(case=c,differences=diff,original=x.hex(),native=y.hex()))
 (out/'results.json').write_text(json.dumps(results,indent=2));print('cases',len(cases),'failed',sum(bool(x['differences']) for x in results),flush=True)
 assert all(not x['differences'] for x in results)
v=dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,custom1=int(os.environ.get('CUSTOM1','0')),extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
machine=os.environ.get('MACHINE','040')
if machine!='040':v['extra_args']='--uae_fpu_no_unimplemented=true'+(' --uae_fpu_model=68882' if machine=='020' else '')
run(machine,out,Path(str(out)+'-seed'),capture,v)
