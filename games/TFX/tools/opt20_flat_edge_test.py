"""Exhaustive guest edge-mask instruction comparison with independent values."""
import os,sys,struct,json,subprocess,re
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
def capture(cmd,dump,bases,hs,out):
 b=bases[0];original=hs[0]['bytes'][0x6c534:0x6c542];candidate=dump('edge-live.bin',b+0x6c534,14)
 assert original.hex()=='761f7820c64198437a1fca425245'
 assert candidate.hex()=='e9c136c578209843e9c256c55245'
 def dc(raw):return ' dc.w '+','.join('$'+raw[i:i+2].hex() for i in range(0,len(raw),2))
 a=[' mc68040',' move.l #2883584,d0',' move.l #$10001,d1',' move.l 4.w,a6',' jsr -198(a6)',' move.l d0,a2',' move.l d0,a3',' move.l #$fedcba98,d0',' move.l #65535,d7','loop:',' move.l d0,d1',' move.w d7,d1',' move.l d0,d2',' swap d2',' move.w d7,d2',' not.w d2',' move.w #31,ccr',dc(original),' movem.l d1-d5,(a2)',' lea 20(a2),a2',' move.w ccr,(a2)+',' move.w #31,ccr',dc(candidate),' movem.l d1-d5,(a2)',' lea 20(a2),a2',' move.w ccr,(a2)+',' rol.l #7,d0',' add.l #$1234567,d0',' dbf d7,loop','finished:',' bra.s finished']
 src=out/'fixture.s';src.write_text('\n'.join(a)+'\n');binary=out/'fixture.bin';lst=out/'fixture.lst'
 subprocess.run(['bash','-c','. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"','fixture',str(src),str(binary),str(lst)],check=True)
 blob=binary.read_bytes();end=len(blob)-2;assert blob[-2:]==bytes.fromhex('60fe');code=b+0x8000
 cmd('delete breakpoints');cmd('monitor tfxreg 16 2700')
 for o in range(0,len(blob),32):cmd(f'monitor tfxmem {code+o:x} {blob[o:o+32].hex()}')
 cmd(f'monitor tfxreg 17 {code:x}');cmd(f'break *{code+end:#x}');reply=cmd('continue');assert f'0x{code+end:08x}' in reply,reply
 cmd('maintenance flush register-cache');address=int(re.search(r'= (0x[0-9a-f]+)',cmd('p/x $a3'))[1],16);cmd(f'monitor tfxsync {address:x} 2883584');data=dump('results.bin',address,2883584)
 for i in range(65536):
  x=data[i*44:i*44+22];y=data[i*44+22:i*44+44];assert x==y,i
  d1,d2,d3,d4,d5,ccr=struct.unpack('>5IH',x);assert d3==d1&31 and d4==32-(d1&31) and d5==(d2&31)+1 and ccr==0,i
 (out/'results.json').write_text(json.dumps(dict(cases=65536,identical_registers_and_ccr=True,independent_mask_oracle=True),indent=2));print('65536 edge pairs: original, candidate and oracle all agree',flush=True)
v=dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040',out,Path(str(out)+'-seed'),capture,v)
