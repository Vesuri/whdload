import json,sys,struct
from harness_a import *
from stack_probe_c import stack_probe
s=Session(sys.argv[1])
try:
 route(s);stats=counters(s,stats_address(s));assert stats['mmu_tc']==0x8000,stats
 raw=read_bytes(s,stats_address(s)+320,32);assert raw[:8]==b'RRCMMU01'
 srp,urp,*ttr=struct.unpack('>6I',raw[8:]);assert not any(v&0x8000 for v in ttr),ttr
 cache={}
 def fetch(addr):
  base=addr&~511
  if base not in cache:cache[base]=read_bytes(s,base,512)
  return struct.unpack_from('>I',cache[base],addr-base)[0]
 def page(addr,root):
  a=fetch((root&0xfffffe00)|((addr>>23)&0x1fc));assert a&2,hex(a)
  b=fetch((a&0xfffffe00)|((addr>>16)&0x1fc));assert b&2,hex(b)
  dp=(b&0xffffff00)+((addr>>10)&0xfc);d=fetch(dp)
  if d&3==2:dp=d&0xfffffffc;d=fetch(dp)
  assert d&1,(hex(addr),hex(d))
  return dict(address=hex(addr),descriptor_address=hex(dp),descriptor=hex(d),physical=hex(d&0xfffff000),cache_mode=(d>>5)&3)
 pages=[page(a,srp) for a in range(0,0x100000,4096)];assert all(x['cache_mode']==0 for x in pages)
 user_pages=[page(a,urp) for a in range(0,0x100000,4096)];assert all(x['cache_mode']==0 for x in user_pages)
 stack=stack_probe(s);fast=[page(rd(s,0x87480),srp),page(int(stack['bottom'],16),srp)];assert all(x['cache_mode']==1 for x in fast),fast
 result=dict(stats=stats,srp=hex(srp),urp=hex(urp),ttr=[hex(v) for v in ttr],base_pages=pages,user_base_pages=user_pages,fast_pages=fast,stack=stack,provenance=provenance(os.environ['SLAVE'],s));(s.out/'policy.json').write_text(json.dumps(result,indent=2)+'\n');print('256 supervisor + 256 user BaseMem pages write-through; Fast code/stack copyback',flush=True)
finally:s.quit()
