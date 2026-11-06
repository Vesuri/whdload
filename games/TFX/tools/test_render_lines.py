"""Compare installed CPU line routines against original hardware blits in chip RAM."""
import os,sys,struct,re,json,subprocess,random
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
cases=[];rng=random.Random(10)
for kind in ['normal','strip']:
 for dx,dy in [(0,0),(0,1),(1,0),(1,1),(2,1),(1,2),(3,1),(1,3),(12,6),(6,12),(31,17),(17,31),(32,31),(31,32),(63,17),(17,63)]:
  for sx,sy in [(1,1),(-1,1),(1,-1),(-1,-1)]:
   cases.append(dict(kind=kind,x0=120,y0=100,x1=120+sx*dx,y1=100+sy*dy,color=rng.randrange(256),pattern=[0xff,0x55,0x81,0x01][len(cases)%4]))
# Exercise all patterns independently of octant, plus screen boundaries.
base_cases=cases;cases=[]
for c in base_cases:
 if c['kind']=='normal':cases.append(c)
 else:
  for pattern in [0,1,0x80,0x81,0x55,0xaa,0x7e,0xff]:cases.append(dict(c,pattern=pattern))
for x0,y0,x1,y1 in [(0,0,319,199),(319,199,0,0),(0,199,319,0),(319,0,0,199),(0,0,319,0),(319,199,0,199),(0,0,0,199),(319,199,319,0)]:
 for kind in ['normal','strip']:cases.append(dict(kind=kind,x0=x0,y0=y0,x1=x1,y1=y1,color=0xa5,pattern=0x96))
def capture(cmd,dump,bases,hs,out):
 b=bases[0];code=b+0x8000
 a=[' mc68040',f' org ${code:x}',' move.l #128128,d0',' move.l #$10003,d1',' move.l 4.w,a6',' jsr -198(a6)',' move.l d0,mem',' move.w #$8240,$dff096']
 for i,c in enumerate(cases):
  a+=[' move.l mem(pc),a0',' lea 64064(a0),a1',' move.w #16015,d7',' move.l #$a55a6996,d0',f'init{i}:',' move.l d0,(a0)+',' move.l d0,(a1)+',' rol.l #3,d0',' add.l #$13ab,d0',f' dbf d7,init{i}']
  for side in [0,1]:
   a+=[' move.l mem(pc),a0',f' lea {32+64064*side}(a0),a0',f' move.w ${bases[1]+0x4930:x},d0',f' move.l a0,(${b+0x4ce00:x},d0.w)']
   args=[c[k] for k in ['color','x0','y0','x1','y1']]+([c['pattern']] if c['kind']=='strip' else [])
   a += [f' move.l #{v},-(sp)' for v in reversed(args)]
   entry='original_'+c['kind'] if side==0 else f'${b+(0x4de00 if c["kind"]=="normal" else 0x500dc):x}'
   a += [f' jsr {entry}',f' lea {4*len(args)}(sp),sp',' tst.b $dff002',f'wait{i}_{side}:',' btst #6,$dff002',f' bne wait{i}_{side}']
  a += [' move.l mem(pc),a0',' lea 64064(a0),a1',' move.w #16015,d7',' moveq #0,d0',f'cmp{i}:',' move.l (a0)+,d1',' cmp.l (a1)+,d1',f' beq next{i}',' addq.l #1,d0',f'next{i}:',f' dbf d7,cmp{i}',f' move.l d0,results+{4*i}']
 a+=['finished:',' bra.s finished','original_normal:',' link a6,#0',' movem.l d2-d6/a0/a2,-(sp)',f' jmp ${b+0x4de08:x}','original_strip:',' link a6,#0',' movem.l d2-d7/a2-a5,-(sp)',f' jmp ${b+0x500e4:x}','mem: dc.l 0','results: ds.l '+str(len(cases))]
 assert hs[0]['bytes'][0x4de00:0x4de08].hex()=='4e56000048e73ea0'
 assert hs[0]['bytes'][0x500dc:0x500e4].hex()=='4e56000048e73f3c'
 src=out/'fixture.s';src.write_text('\n'.join(a)+'\n');bin=out/'fixture.bin';lst=out/'fixture.lst'
 subprocess.run(['bash','-c','. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"','fixture',str(src),str(bin),str(lst)],check=True)
 labels={n:int(re.search(r'^'+n+r'\s+A:([0-9A-Fa-f]+)',lst.read_text(),re.M)[1],16) for n in ['finished','results','mem']};blob=bin.read_bytes();assert len(blob)<0x30000
 cmd('delete breakpoints');cmd('monitor tfxreg 16 2700')
 for off in range(0,len(blob),32):cmd(f'monitor tfxmem {code+off:x} {blob[off:off+32].hex()}')
 cmd(f'monitor tfxreg 17 {code:x}');cmd(f'break *{labels["finished"]:#x}');reply=cmd('continue');assert f'0x{labels["finished"]:08x}' in reply,reply
 cmd(f'monitor tfxsync {labels["results"]:x} {len(cases)*4}');data=dump('results.bin',labels['results'],len(cases)*4)
 for i,c in enumerate(cases):c['different_longs']=struct.unpack_from('>I',data,4*i)[0]
 (out/'results.json').write_text(json.dumps(cases,indent=2));print('lines',len(cases),'different',sum(bool(x['different_longs']) for x in cases),flush=True)
 cmd(f'monitor tfxsync {labels["mem"]:x} 4');memory=struct.unpack('>I',dump('allocation.bin',labels['mem'],4))[0];assert 0<memory<0x200000-128128
 dump('last-buffers.bin',memory,128128)
 if not os.environ.get('ALLOW_DIFFERENCES'):assert not any(x['different_longs'] for x in cases)
v=dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040',out,Path(str(out)+'-seed'),capture,v)
