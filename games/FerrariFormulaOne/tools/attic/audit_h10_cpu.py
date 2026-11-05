from pathlib import Path
import sys,json,re,struct,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];base=int(r['probe'],16);listing=(Path(r['slave']).parent/'fine/fine.list').read_text()
rows=[int(m[1],16) for m in re.finditer(r'^00:([0-9A-F]{8}) [0-9A-F]+\s+\d+:\s+movem.l d0-d6/a0-a4,\(a5\)',listing,re.M) if sy.get('FF1RenderClearRows',sy.get('H10BenchFill'))<=int(m[1],16)<sy.get('FF1RenderClearControl',sy.get('H10BenchControl'))];assert len(rows)==1
site=base+rows[0];trace=barto.load(p/'detail.bin');result=[]
for f in trace.fields:
 expected=collections.Counter();actual=collections.Counter();fetched=set();destinations=set();fetch_slots=collections.defaultdict(list);write_slots=collections.defaultdict(list)
 for pc,c,g in trace.instructions(f):
  if pc==site:
   assert not (g[16]>>8)&7
   assert g[0] in (0,0xffffffff)
   assert all(g[i]==g[0] for i in list(range(7))+list(range(8,13)))
   assert 0<=g[13] and g[13]+48<=0x200000
   for off in range(0,48,2):expected[(g[13]+off,g[0]&65535)]+=1;destinations.add(g[13]+off)
 for at in range(0,len(f.dma),f.dma_size):
  typ=struct.unpack_from('<h',f.dma,at+29)[0];address=struct.unpack_from('<I',f.dma,at+12)[0];reg=struct.unpack_from('<H',f.dma,at)[0];value=struct.unpack_from('<Q',f.dma,at+2)[0]
  if typ==6:fetched.add(address&~1);fetch_slots[address&~1].append(at//f.dma_size)
  if reg==0x1102:actual[(address,value&65535)]+=1;write_slots[(address,value&65535)].append(at//f.dma_size)
  if reg==0x1104:
   actual[(address,(value>>16)&65535)]+=1;actual[(address+2,value&65535)]+=1;write_slots[(address,(value>>16)&65535)].append(at//f.dma_size);write_slots[(address+2,value&65535)].append(at//f.dma_size)
 # A row's instruction can straddle the field boundary. Compare complete
 # trace totals below, retaining individual field read/write intersections.
 timings=[]
 for key in expected:
  fs=fetch_slots[key[0]];ws=write_slots[key]
  if fs and ws:
   assert max(ws)<min(fs) or min(ws)>max(fs),(f.index,key,fs,ws)
   timings.append('before' if max(ws)<min(fs) else 'after')
 result.append(dict(fetch_relation=dict(collections.Counter(timings)),field=f.index,expected=expected,actual=actual,display_overlap=len(destinations&fetched),rows=sum(expected.values())//24))
e=collections.Counter();a=collections.Counter()
for x in result:e.update(x.pop('expected'));a.update(x.pop('actual'))
bad={str(k):(v,a[k]) for k,v in e.items() if a[k]<v};assert not bad,list(bad.items())[:5]
# Actual transfers can include unrelated writers to the same destination.
# Require every generated word/pattern to appear on the Chip bus.
out=dict(status='passed',rows=sum(x['rows'] for x in result),word_stores=sum(e.values()),all_selected_stores_observed_on_chip_bus=True,fields=result,scope='CPU clear row operands/patterns and actual Chip word transactions; each observed clear word is outside its display-fetch interval. Complete RGB gates separately cover scanout.')
(p/'h10-cpu-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
