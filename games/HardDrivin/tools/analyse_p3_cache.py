from pathlib import Path
import sys,json,re,struct,collections
import barto_mmap as barto
for name in sys.argv[1:]:
 p=Path('tmp/prof')/name;meta=json.loads((p/'metadata.json').read_text());listing=(p/'slave.lst').read_text(encoding='latin1')
 sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',listing,re.M)};base=meta['layout']['published']-sy['_code_start']
 lo=sy['_phase_engine_call'];hi=sy['_phase_initialize'];code=(p/'before-slow.bin').read_bytes();codebase=0xc00000
 # Branches to .miss appear in the listing in audited key order.
 branches=[]
 for line in listing.splitlines():
  m=re.match(r'00:([0-9A-F]+)\s+[0-9A-F]+\s+\d+:\s+(?:beq|bne)(?:\.\w+)?\s+\.miss\s*$',line)
  if m and lo<=int(m[1],16)<hi:branches.append(base+int(m[1],16))
 labels=['new phase','invalid','anchor velocity','anchor RPM','gear','throttle','brake','contact mask','skid','road','turning','grade disabled','engine disabled','automatic','pitch sine']
 assert len(branches)==len(labels),(len(branches),branches)
 # Decode the first word-sized branch destination.
 off=branches[0]-codebase;op,disp=struct.unpack_from('>Hh',code,off);assert op&255==0;miss=branches[0]+2+disp
 hits=collections.Counter();last=None;t=barto.load(p/'trace.bin')
 for field in t.fields:
  for pc,cyc,regs in t.instructions(field):
   if pc is None or not(base+lo<=pc<base+hi):continue
   if pc==miss and last in branches:hits[labels[branches.index(last)]]+=1
   last=pc
 i=code.find(b'HDENGC01')+8;after=(p/'after-slow.bin').read_bytes();offset=sy['_phase_cache_hits']-sy['_phase_cache_valid'];beforecounts=struct.unpack_from('>II',code,i+offset);aftercounts=struct.unpack_from('>II',after,i+offset);ch,cm=[a-b for a,b in zip(aftercounts,beforecounts)]
 out=dict(cache_hits=ch,cache_misses=cm,hit_rate=ch/(ch+cm),miss_reasons=dict(hits));(p/'engine-cache.json').write_text(json.dumps(out,indent=2)+'\n');print(name,out)
