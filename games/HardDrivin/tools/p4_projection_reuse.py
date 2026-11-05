from pathlib import Path
import json,re,sys,collections
import barto_mmap as b
for name in sys.argv[1:]:
 p=Path('tmp/prof')/name;m=json.loads((p/'metadata.json').read_text());listing=(p/'slave.lst').read_text(encoding='latin1')
 sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',listing,re.M)}
 base=m['layout']['published']-sy['_code_start'];target=base+sy['_projection_integer_components'];entry=m['layout']['code_base']+0xcda4
 t=b.load(p/'trace.bin');seen=set();recent=[];calls=0;frames=0;hits=collections.Counter();values=collections.Counter()
 for f in t.fields:
  for pc,c,r in t.instructions(f):
   if pc==entry:frames+=1;seen.clear();recent=[]
   if pc!=target:continue
   v=r[0]&65535;calls+=1;values[v]+=1
   for n in [1,2,4]:hits[str(n)]+=v in recent[-n:]
   hits['unlimited']+=v in seen
   seen.add(v);recent.append(v)
 report=dict(calls=calls,physics_entries=frames,hits=dict(hits),scope='Optimistic per-physics-frame reuse by integer velocity alone, ignoring trig changes and lookup cost; measures opportunity only, not a valid cache design.')
 (p/'projection-reuse.json').write_text(json.dumps(report,indent=2)+'\n');print(name,report,flush=True)
