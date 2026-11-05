import re,json,sys,collections
from pathlib import Path
import barto_mmap as b
p=Path('tmp/prof')/sys.argv[1];m=json.loads((p/'metadata.json').read_text());lst=(p/'slave.lst').read_text(encoding='latin1');sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9a-fA-F]+)',lst,re.M)};base=m['layout']['published']-sy['_code_start'];counts=collections.Counter();t=b.load(p/'trace.bin');low=base+sy['_traffic_speed_step'];high=base+sy['_traffic_collision']
for f in t.fields:
 for pc,c,r in t.instructions(f):
  if pc is not None and low<=pc<high:counts[pc-base]+=1
for line in lst.splitlines():
 match=re.match(r'00:([0-9A-Fa-f]+)\s',line)
 if match and int(match[1],16) in counts:print(counts[int(match[1],16)],line)
