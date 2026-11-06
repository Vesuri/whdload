"""Guest tests of actual delta copy helper, two buffer histories and guards."""
import os,sys,json,struct,subprocess,re
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
listing=Path(os.environ['DELTA_LISTING']).read_text(encoding='latin1')
def offset(n):return int(re.search(r'^'+re.escape(n)+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
N=80

def capture(cmd,dump,bases,hs,out):
 b=bases[0];code=b+0x8000;sb=int.from_bytes(dump('swap-target.bin',b+0x19fe,4),'big')-offset('do_swap_screen')
 logptr=int.from_bytes(dump('logbase-pointer.bin',sb+offset('_logbase_ptr'),4),'big')
 a=[' mc68040',f' org ${code:x}',' move.l #320256,d0',' move.l #$10001,d1',' move.l 4.w,a6',' jsr -198(a6)',' move.l d0,mem',' move.l d0,a0',' move.l #80063,d7','init:',' move.l #$a55a6996,(a0)+',' subq.l #1,d7',' bpl init',' move.l mem(pc),a0',' lea 192224(a0),a1',f' move.l a1,${sb+offset("delta_shadow"):x}',f' clr.l ${sb+offset("delta_seen"):x}',f' clr.l ${sb+offset("delta_seen")+4:x}',' lea 32(a0),a1',' move.w #15999,d7','blank:',' clr.l (a1)+',' dbf d7,blank']
 # Source edits exercise every mismatch position in the 16-byte block, both ends,
 # repeated identical frames, all-changed frames and alternating chip buffers.
 for i in range(N):
  a += [' move.l mem(pc),a0',' lea 32(a0),a1']
  if i%16==8:
   a += [' move.w #15999,d7',f' move.l #${(0x12345678+i):x},d0',f'fill{i}:',' move.l d0,(a1)+',' rol.l #3,d0',' add.l #$13ab,d0',f' dbf d7,fill{i}']
  elif i>1 and i%4!=0:
   for k in [0,1,7,3999]:a += [f' move.l #${((i*0x1020304+k)&0xffffffff):x},{k*16+(i%4)*4}(a1)']
   # Every longword of a 32-byte line, two units of one line, the last longword.
   for k,o in enumerate([3200+(i%8)*4,6400+(i%8)*4,6400+((i+3)%8)*4,9600+(i%8)*4,9628,63996]):a += [f' move.l #${((i*0x2040608+k)&0xffffffff):x},{o}(a1)']
  page=i%2
  a += [f' move.w #{page*4},${logptr:x}',' move.l mem(pc),a0',' lea 32(a0),a1',f' lea {64096+page*64064}(a0),a0',f' jsr ${sb+offset("copy_changed_blocks"):x}',f' move.l a0,pointers+{i*8}',f' move.l a1,pointers+{i*8+4}',' move.l mem(pc),a0',' lea 32(a0),a1',f' lea {64096+page*64064}(a0),a2',f' lea {192224+page*64000}(a0),a3',' moveq #0,d0',' move.w #15999,d7',f'check{i}:',' move.l (a1)+,d1',' cmp.l (a2)+,d1',f' beq dstok{i}',' addq.l #1,d0',f'dstok{i}:',' cmp.l (a3)+,d1',f' beq shadowok{i}',' addq.l #1,d0',f'shadowok{i}:',f' dbf d7,check{i}',f' move.l d0,results+{i*4}']
 a += ['finished: bra.s finished','mem: dc.l 0',f'results: ds.l {N}',f'pointers: ds.l {N*2}']
 src=out/'fixture.s';src.write_text('\n'.join(a)+'\n');binary=out/'fixture.bin';lst=out/'fixture.lst'
 subprocess.run(['bash','-c','. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"','fixture',str(src),str(binary),str(lst)],check=True)
 labels={n:int(re.search(r'^'+n+r'\s+A:([0-9A-Fa-f]+)',lst.read_text(),re.M)[1],16) for n in ['finished','mem','results','pointers']};blob=binary.read_bytes();assert len(blob)<0x3b000
 cmd('delete breakpoints');cmd('monitor tfxreg 16 2700')
 for off in range(0,len(blob),32):cmd(f'monitor tfxmem {code+off:x} {blob[off:off+32].hex()}')
 cmd(f'monitor tfxreg 17 {code:x}');cmd(f'break *{labels["finished"]:#x}');reply=cmd('continue');assert f'0x{labels["finished"]:08x}' in reply,reply[-1000:]
 cmd(f'monitor tfxsync {labels["mem"]:x} {4+N*12}');addr=int.from_bytes(dump('allocation.bin',labels['mem'],4),'big');results=struct.unpack('>'+str(N)+'I',dump('results.bin',labels['results'],N*4));ptrs=struct.unpack('>'+str(N*2)+'I',dump('pointers.bin',labels['pointers'],N*8))
 cmd(f'monitor tfxsync {addr:x} 320256');data=dump('outputs.bin',addr,320256)
 guards=[(0,32),(64032,64096),(128096,128160),(192160,192224),(320224,320256)]
 guardok=all(data[x:y]==bytes.fromhex('a55a6996')*((y-x)//4) for x,y in guards)
 ptrok=all(ptrs[i*2]==addr+64096+(i%2)*64064+64000 and ptrs[i*2+1]==addr+64032 for i in range(N))
 result=dict(cases=N,different_longs=list(results),guards=guardok,pointers=ptrok);(out/'results.json').write_text(json.dumps(result,indent=2));assert not any(results) and guardok and ptrok,result
 print('PASS',N,'delta copy cases',flush=True)
v=dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040',out,Path(str(out)+'-seed'),capture,v)
