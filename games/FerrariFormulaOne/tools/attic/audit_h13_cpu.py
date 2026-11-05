from pathlib import Path
import sys,json,re,struct,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];base=int(r['probe'],16);listing=(Path(r['slave']).parent/'fine/fine.list').read_text()
lo=sy.get('FF1RenderGaugeStrip',sy.get('H13Gauge'));hi=sy.get('FF1RenderGaugeControl',sy.get('H13Control'))
sites=[int(m[1],16) for m in re.finditer(r'^00:([0-9A-F]{8}) [0-9A-F]+\s+\d+:\s+move.w d1,\(a1\)\+',listing,re.M) if lo<=int(m[1],16)<hi];assert len(sites)==1;site=base+sites[0]
m=(p/'canonical.bin').read_bytes();planes=struct.unpack_from('>3I',m,0x1fdb8);assert all(0<a<a+1368<=0x200000 for a in planes)
e=collections.Counter();actual=collections.Counter();fetches=set();t=barto.load(p/'detail.bin')
for f in t.fields:
 for pc,c,g in t.instructions(f):
  if pc!=site:continue
  assert not (g[16]>>8)&7
  dst=g[9];assert any(a<=dst< a+1368 for a in planes),(hex(dst),planes)
  assert not dst&1;e[(dst,g[1]&65535)]+=1
 for at in range(0,len(f.dma),f.dma_size):
  typ=struct.unpack_from('<h',f.dma,at+29)[0];address=struct.unpack_from('<I',f.dma,at+12)[0];reg=struct.unpack_from('<H',f.dma,at)[0];value=struct.unpack_from('<Q',f.dma,at+2)[0]
  if typ==6:fetches.add(address&~1)
  if reg==0x1102:actual[(address,value&65535)]+=1
  elif reg==0x1104:actual[(address,value>>16&65535)]+=1;actual[(address+2,value&65535)]+=1
assert e
assert all(actual[k]>=v for k,v in e.items())
assert not {k[0] for k in e}&fetches
out=dict(status='passed',word_stores=sum(e.values()),source_planes=list(map(hex,planes)),all_selected_stores_observed_on_chip_bus=True,display_fetch_overlap=False,scope='Gauge stores remain within the existing cockpit Chip planes; no displayed bitplane fetch overlaps those CPU destinations.')
(p/'h13-cpu-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
