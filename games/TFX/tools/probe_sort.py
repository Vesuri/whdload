#!/usr/bin/env python3
import os,json,re,struct,random,sys
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();machine=sys.argv[2] if len(sys.argv)>2 else '040';os.chdir(ROOT)
def capture(cmd,dump,bases,hs,out):
 b=bases[0]
 cmd('delete breakpoints')
 for hook,size in [(0x5efbe,32),(0x5f03e,14)]:dump(f'hook-{hook:x}.bin',b+hook,size)
 cmd(f'break *{b+0x5f04c:#x}')
 results=[]
 for pattern in ['ascending','descending','random','equal']:
  n=348;r=random.Random(7)
  values=list(range(n)) if pattern=='ascending' else list(range(n))[::-1] if pattern=='descending' else [r.randrange(-30000,30000) for _ in range(n)] if pattern=='random' else [123]*n
  values[0]=-32768
  data=struct.pack('>hhh',n,n-1,0)+struct.pack('>'+str(n)+'h',*values)+struct.pack('>'+str(n)+'H',*range(n))+b'GUARD!!!'
  p=out/'input.bin';p.write_bytes(data)
  for off in range(0,len(data),32):cmd(f'monitor tfxmem {b+0x5bf10+off:x} {data[off:off+32].hex()}')
  assert dump('injected.bin',b+0x5bf10,len(data))==data
  cmd(f'monitor tfxreg 1 15c')
  cmd(f'monitor tfxreg 17 {b+0x5f03e:x}')
  reply=cmd('continue');assert f'0x{b+0x5f04c:08x}' in reply,reply
  cmd(f'monitor tfxsync {b+0x5bf10:x} {len(data)}')
  d=dump(pattern+'.bin',b+0x5bf10,len(data));depth=list(struct.unpack_from('>348h',d,6));idx=list(struct.unpack_from('>348H',d,702))
  result=dict(pattern=pattern,sorted=depth==sorted(values),permutation=sorted(idx)==list(range(n)),paired=all(i<n and v==values[i] for v,i in zip(depth,idx)),guard=d[-8:]==b'GUARD!!!',changed=[i for i,(x,y) in enumerate(zip(data,d)) if x!=y])
  results.append(result);print({k:v for k,v in result.items() if k!='changed'},flush=True)
 (out/'results.json').write_text(json.dumps(results,indent=2))
v=dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true' if machine=='040' else '')
run(machine,out,Path(os.environ['TEST_SEED']) if 'TEST_SEED' in os.environ else out.parent/(out.name+'-seed'),capture,v)
