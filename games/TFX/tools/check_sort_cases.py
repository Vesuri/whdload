#!/usr/bin/env python3
"""Exercise native sort call sites in a loaded game; requires private fixture backend."""
import os,sys,json,struct,random,re
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();machine=sys.argv[2] if len(sys.argv)>2 else '040';os.chdir(ROOT)
def capture(cmd,dump,bases,hs,out):
 b=bases[0];cmd('delete breakpoints');results=[]
 def write(a,d):
  for off in range(0,len(d),32):cmd(f'monitor tfxmem {a+off:x} {d[off:off+32].hex()}')
  assert dump('injected.bin',a,len(d))==d
 def reg(n,v):cmd(f'monitor tfxreg {n} {v:x}')
 def getreg(n):
  cmd('maintenance flush register-cache');return int(re.search(r'= (0x[0-9a-f]+)',cmd(f'p/x ${n}'))[1],16)
 sp=getreg('sp');savedsp=dump('stack.bin',sp,8)
 for hook,size in [(0x5efbe,32),(0x5f03e,14)]:
  d=dump(f'hook-{hook:x}.bin',b+hook,size);assert d[:2]==bytes.fromhex('4eb9')
 for mode,n,pattern in [('draw',n,'random') for n in [0,1,2,6,7,14,15,347,348]]+[('add',348,p) for p in ['ascending','descending','equal','random']]:
  r=random.Random(7);values=list(range(348)) if pattern=='ascending' else list(range(348))[::-1] if pattern=='descending' else [123]*348 if pattern=='equal' else [r.randrange(-30000,30000) for _ in range(348)]
  # AddObject's full path inserts index 347, then sorts all 348 entries.
  count=347 if mode=='add' else n
  data=struct.pack('>hhh',count,347,0)+struct.pack('>348h',*values)+struct.pack('>348H',*range(348))+b'GUARD!!!'
  write(b+0x5bf10,data);reg(15,sp)
  for i in range(2,15):reg(i,0x12000000+i*0x100)
  if mode=='add':
   write(sp,struct.pack('>I',b+0x19fc));reg(0,values[347]&0xffff);start=0x5efe8;end=0x19fc
  else:start=0x5efbe;end=0x5efde
  cmd(f'break *{b+end:#x}');reg(17,b+start);reply=cmd('continue');assert f'0x{b+end:08x}' in reply
  cmd('delete breakpoints')
  cmd(f'monitor tfxsync {b+0x5bf10:x} {len(data)}')
  d=dump(f'{mode}-{n}-{pattern}.bin',b+0x5bf10,len(data));dep=list(struct.unpack_from('>348h',d,6));idx=list(struct.unpack_from('>348H',d,702))
  assert dep[:n]==sorted(values[:n]),(mode,n,'depth')
  assert sorted(idx[:n])==list(range(n)),(mode,n,'indices')
  assert all(dep[j]==values[idx[j]] for j in range(n)),(mode,n,'pairing')
  assert dep[n:]==values[n:] and idx[n:]==list(range(n,348)) and d[-8:]==b'GUARD!!!'
  preserve=[i for i in range(2,15) if i!=7] if mode=='add' else [10,11]
  assert all(getreg(('d'+str(i)) if i<8 else ('a'+str(i-8)))==0x12000000+i*0x100 for i in preserve)
  assert getreg('sp')==sp+(4 if mode=='add' else 0)
  if mode=='add':
   assert struct.unpack_from('>HH',d)==(348,idx[347])
   assert getreg('d7')==0x1200015c # Original AddObject changes D7 before saving registers.
  results.append(dict(mode=mode,count=n,pattern=pattern,passed=True));print(results[-1],flush=True)
 (out/'results.json').write_text(json.dumps(results,indent=2))
v=dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true' if machine=='040' else '')
run(machine,out,out.parent/(out.name+'-seed'),capture,v)
