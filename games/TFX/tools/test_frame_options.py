"""Actual installed timestep adapters: zero-time skip, FPU stack ABI, zoom clamp."""
import os,sys,re,struct,json,subprocess
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
def capture(cmd,dump,bases,hs,out):
 b=bases[0];code=b+0x6000
 entries={}
 for o,h in [(0x1830,'302cf45c48c0'),(0x1850,'302cf45c48c0'),(0x1ec38,'102cf45a5300'),(0x1fec4,'4c7c18010000001e')]:
  assert hs[0]['bytes'][o:o+len(h)//2].hex()==h
  raw=dump(f'hook-{o:x}.bin',b+o,6);assert raw[:2]==b'\x4e\xb9';entries[o]=struct.unpack('>I',raw[2:])[0]
 assert dump('limit.bin',b+0x1abfe,2)==bytes.fromhex('7000')
 assert hs[0]['bytes'][0x1e914:0x1e91c].hex()=='514ff227e09c2f07'
 assert hs[0]['bytes'][0x1ee7a:0x1ee84].hex()=='2e1ff21fd039504f4e75'
 cmd('maintenance flush register-cache');a4=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $a4'))[1],16)
 a=[' mc68040',f' org ${code:x}',f' move.l #${a4:x},a4'];records=[]
 def store(lines,expected,kind):
  idx=len(records);a.extend(lines+[f' movem.l d0-d3,results+{idx*16}']);records.append(dict(kind=kind,expected=[v&0xffffffff for v in expected]))
 for site in [0x1830,0x1850]:
  for delta in [0,1,2,5,55,32767,-1]:
   idx=len(records)
   store([f' move.w #{delta},(-$ba4,a4)',' move.l #$a5a5a5a5,d0',' moveq #0,d1',' moveq #0,d2',' moveq #0,d3',f' jsr ${entries[site]:x}',f' bsr.w updated{idx}',f' bra.s next{idx}',f'updated{idx}:',' moveq #1,d1',' rts',f'next{idx}:'],[delta,int(delta!=0),0,0],f'skip-{site:x}')
 for delta in [0,1,5,55]:
  for mode in [0,1,2,255]:
   idx=len(records)
   a += [f' move.w #{delta},(-$ba4,a4)',f' move.b #{mode},(-$ba6,a4)',' move.l sp,before_sp',' move.l #$12345678,d7',' move.l #$a5a5a500,d0',' moveq #0,d1',' fmove.l #7,fp2',' fmove.l #8,fp3',' fmove.l #9,fp4',' fmove.l #10,fp7',f' bsr model{idx}',' move.l sp,d2',' sub.l before_sp(pc),d2',' move.l d7,d3',f' bra model_done{idx}',f'model{idx}:',' subq.w #8,sp',' fmovem.x fp2-fp4/fp7,-(sp)',' move.l d7,-(sp)',' moveq #77,d7',' fmove.l #42,fp2',f' jsr ${entries[0x1ec38]:x}',' moveq #1,d1',' move.l (sp)+,d7',' fmovem.x (sp)+,fp2-fp4/fp7',' addq.w #8,sp',' rts',f'model_done{idx}:',f' fmovem.x fp2-fp4/fp7,fpresults+{(idx-14)*48}']
   store([],[(0xa5a5a500|((mode-1)&255)) if delta else 0xa5a5a500,int(delta!=0),0,0x12345678],'model')
 for value in [0,1,-1,29,-29,30,-30,31,60,2**31-1,-2**31]:
  q=abs(value)//30*(-1 if value<0 else 1);q=q or 1
  store([f' move.l #{value},d1',' moveq #0,d0',' moveq #0,d2',' moveq #0,d3',f' jsr ${entries[0x1fec4]:x}'],[0,q,0,0],'zoom')
 a+=['finished:',' bra.s finished','before_sp: dc.l 0','fpresults: ds.b 768','results: ds.b '+str(len(records)*16)]
 src=out/'fixture.s';src.write_text('\n'.join(a)+'\n');bin=out/'fixture.bin';lst=out/'fixture.lst'
 subprocess.run(['bash','-c','. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"','fixture',str(src),str(bin),str(lst)],check=True)
 labels={n:int(re.search(r'^'+n+r'\s+A:([0-9A-Fa-f]+)',lst.read_text(),re.M)[1],16) for n in ['finished','results','fpresults']}
 blob=bin.read_bytes();cmd('delete breakpoints');cmd('monitor tfxreg 16 2700')
 for o in range(0,len(blob),32):cmd(f'monitor tfxmem {code+o:x} {blob[o:o+32].hex()}')
 cmd(f'monitor tfxreg 17 {code:x}');cmd(f'break *{labels["finished"]:#x}');reply=cmd('continue');assert f'0x{labels["finished"]:08x}' in reply,reply
 for name,size in [('results',len(records)*16),('fpresults',768)]:cmd(f'monitor tfxsync {labels[name]:x} {size}');dump(name+'.bin',labels[name],size)
 data=(out/'results.bin').read_bytes()
 for i,item in enumerate(records):item['actual']=list(struct.unpack_from('>IIII',data,16*i));item['equal']=item['actual']==item['expected']
 fp=(out/'fpresults.bin').read_bytes();expect=['40010000e000000000000000','400200008000000000000000','400200009000000000000000','40020000a000000000000000']
 clean=lambda x:x[:2]+x[4:]
 for i in range(16):assert [clean(fp[i*48+j*12:i*48+j*12+12]) for j in range(4)]==[clean(bytes.fromhex(x)) for x in expect]
 (out/'results.json').write_text(json.dumps(records,indent=2));print('options',len(records),'passed',sum(x['equal'] for x in records),flush=True);assert all(x['equal'] for x in records)
v=dict(executable='tfx.020',custom3=3,custom4=50,swap=0x19fc,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040',out,Path(str(out)+'-seed'),capture,v)
