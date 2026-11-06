"""Native original/candidate sprite twins with independent byte-level oracle."""
import os,sys,json,struct,subprocess,re,random
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
r=random.Random(2040)
cases=[dict(shift=i%16,width=[1,2,3,7,20,63][(i//16)%6],height=[1,2,8][i%3],first=[65535,0,0xa55a][i%3],last=[0xffff,0,0x6996][(i//3)%3],sm=[0,2,6][i%3],dm=[0,2,8][(i//3)%3],odd=i%2) for i in range(192)]
def pattern(seed,n=4096):
 b=bytearray()
 for i in range(n//4):
  b+=struct.pack('>I',seed);seed=(((seed<<3)|(seed>>29))+0x13ab)&0xffffffff
 return b
mask=pattern(0x12345678);pixels=pattern(0x87654321);initial=pattern(0xa55a6996)
def oracle(c):
 d=initial.copy();mp=32+c['odd'];ip=32+c['odd'];dp=32
 for y in range(c['height']):
  for x in range(c['width']):
   m=int.from_bytes(mask[mp:mp+2],'big');v=int.from_bytes(pixels[ip:ip+2],'big')
   if x==0:m &=c['first']
   if x==c['width']-1:m &=c['last']
   m<<=16-c['shift'];v<<=16-c['shift'];old=int.from_bytes(d[dp:dp+4],'big')
   d[dp:dp+4]=((old&(~m&0xffffffff))|(v&m)).to_bytes(4,'big')
   mp+=2;ip+=2;dp+=2
  mp+=c['sm'];ip+=c['sm'];dp+=c['dm']
 return d

def capture(cmd,dump,bases,hs,out):
 b=bases[0];code=b+0x8000;param=b+0x4e518
 assert hs[0]['bytes'][0x4e53a:0x4e542].hex()=='48e782d8207affea'
 assert dump('sprite-patch.bin',b+0x4e53a,6)[:2]==bytes.fromhex('4ef9')
 a=[' mc68040',f' org ${code:x}',f' move.l #{8192+len(cases)*8192},d0',' move.l #$10001,d1',' move.l 4.w,a6',' jsr -198(a6)',' move.l d0,mem',' move.l d0,a0']
 for k,seed in enumerate([0x12345678,0x87654321]):
  a += [f' move.l #${seed:x},d0',' move.w #1023,d7',f'src{k}:',' move.l d0,(a0)+',' rol.l #3,d0',' add.l #$13ab,d0',f' dbf d7,src{k}']
 for i,c in enumerate(cases):
  a += [' move.l mem(pc),a0',f' lea {8192+i*8192}(a0),a0',' move.l a0,a1',' lea 4096(a0),a2',' move.l #$a55a6996,d0',' move.w #1023,d7',f'init{i}:',' move.l d0,(a1)+',' move.l d0,(a2)+',' rol.l #3,d0',' add.l #$13ab,d0',f' dbf d7,init{i}']
  for side in [0,1]:
   a += [f' lea ${param:x},a6',f' move.l #${(c["first"]<<16)|c["last"]:x},(a6)',f' move.w #${(c["shift"]<<12)|0xfca:x},4(a6)',f' move.w #{(c["height"]<<6)|c["width"]},8(a6)',f' move.w #{c["sm"]},10(a6)',f' move.w #{c["sm"]},12(a6)',f' move.w #{c["dm"]},16(a6)',' move.l mem(pc),a0',f' lea {32+c["odd"]}(a0),a1',' move.l a1,18(a6)',' lea 4096(a1),a1',' move.l a1,22(a6)',f' lea {8192+i*8192+side*4096+32}(a0),a1',' move.l a1,30(a6)']
   a += [' move.l #$1234,d0',' move.l #$5678,d6',' move.l #$1111,a0',' move.l #$2222,a1',' move.l #$3333,a3',' move.l #$4444,a4',' move.l #$5555,a6',f' jsr '+('original' if side==0 else f'${b+0x4e53a:x}'),f' movem.l d0/d6/a0-a1/a3-a4/a6,regs+{(i*2+side)*28}']
 a += ['finished: bra.s finished','original:',' movem.l d0/d6/a0-a1/a3-a4,-(sp)',f' move.l ${b+0x4e52a:x},a0',f' jmp ${b+0x4e542:x}','mem: dc.l 0',f'regs: ds.b {len(cases)*56}']
 src=out/'fixture.s';src.write_text('\n'.join(a)+'\n');binary=out/'fixture.bin';listing=out/'fixture.lst'
 subprocess.run(['bash','-c','. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"','fixture',str(src),str(binary),str(listing)],check=True)
 labels={n:int(re.search(r'^'+n+r'\s+A:([0-9A-Fa-f]+)',listing.read_text(),re.M)[1],16) for n in ['finished','mem','regs']};blob=binary.read_bytes();assert len(blob)<0x3b000
 cmd('delete breakpoints');cmd('monitor tfxreg 16 2700')
 for off in range(0,len(blob),32):cmd(f'monitor tfxmem {code+off:x} {blob[off:off+32].hex()}')
 cmd(f'monitor tfxreg 17 {code:x}');cmd(f'break *{labels["finished"]:#x}');reply=cmd('continue');assert f'0x{labels["finished"]:08x}' in reply,reply[-1000:]
 cmd(f'monitor tfxsync {labels["mem"]:x} {4+len(cases)*56}');addr=int.from_bytes(dump('allocation.bin',labels['mem'],4),'big');regs=dump('regs.bin',labels['regs'],len(cases)*56)
 cmd(f'monitor tfxsync {addr:x} {8192+len(cases)*8192}');data=dump('outputs.bin',addr,8192+len(cases)*8192)
 sentinel=struct.pack('>7I',0x1234,0x5678,0x1111,0x2222,0x3333,0x4444,0x5555)
 result=[]
 for i,c in enumerate(cases):
  old=data[8192+i*8192:8192+i*8192+4096];new=data[8192+i*8192+4096:8192+(i+1)*8192];expected=oracle(c)
  result.append(dict(c,original_equal=old==expected,candidate_equal=new==expected,registers_equal=regs[i*56:(i+1)*56]==sentinel*2,changed=sum(a!=b for a,b in zip(expected,initial))))
 (out/'results.json').write_text(json.dumps(result,indent=2));assert all(c['original_equal'] and c['candidate_equal'] and c['registers_equal'] for c in result),[c for c in result if not(c['original_equal'] and c['candidate_equal'] and c['registers_equal'])][:3]
 print('PASS',len(cases),'sprite cases',flush=True)
v=dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040',out,Path(str(out)+'-seed'),capture,v)
