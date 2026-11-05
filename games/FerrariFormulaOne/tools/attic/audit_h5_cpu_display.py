from pathlib import Path
import sys,json,re,struct,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];base=int(r['probe'],16);listing=(Path(r['slave']).parent/'fine/fine.list').read_text();sites={}
for line in listing.splitlines():
 m=re.match(r'^00:([0-9A-F]{8}) [0-9A-F]+\s+\d+:\s+move.b d[01],(?:(\d+))?\(a1\)',line)
 if m and sy['FF1RenderBitmap']<=int(m[1],16)<sy['FF1RenderBitmapControl']:sites[base+int(m[1],16)]=int(m[2] or 0)
assert len(sites)==8,sites
trace=barto.load(p/'detail.bin');fields=[]
for f in trace.fields:
 reads=set(); fetches=collections.defaultdict(list); cpu_writes=collections.defaultdict(list)
 for at in range(0,len(f.dma),f.dma_size):
  typ=struct.unpack_from('<h',f.dma,at+29)[0];address=struct.unpack_from('<I',f.dma,at+12)[0]
  slot=at//f.dma_size;reg=struct.unpack_from('<H',f.dma,at)[0]
  if typ==6 and address!=0xffffffff:
   reads.add(address&~1);fetches[address&~1].append(slot)
  if reg==0x1101:cpu_writes[address].append(slot)
 writes=[]
 for pc,c,g in trace.instructions(f):
  if pc in sites and not (g[16]>>8)&7:writes.append(g[9]+sites[pc])
 overlap=sorted(set(x&~1 for x in writes)&reads)
 counts=collections.Counter(writes)
 for address,count in counts.items():assert len(cpu_writes[address])==count,(f.index,hex(address),count,cpu_writes[address])
 timing=None
 if overlap:
  fetch_slots=[slot for word in overlap for slot in fetches[word]]
  write_slots=[slot for address in counts if address&~1 in overlap for slot in cpu_writes[address]]
  # Require ALL affected words/planes to have been fetched before ANY update.
  # This is stronger than a row-by-row non-overlap test and excludes torn glyphs.
  timing=dict(last_affected_fetch_slot=max(fetch_slots),first_affected_write_slot=min(write_slots),last_affected_write_slot=max(write_slots),all_writes_after_all_fetches=min(write_slots)>max(fetch_slots),margin_slots=min(write_slots)-max(fetch_slots))
 fields.append(dict(field=f.index,cpu_glyph_byte_writes=len(writes),displayed_word_overlap=[hex(x) for x in overlap],timing=timing))
result=dict(status='passed' if all(not x['displayed_word_overlap'] or x['timing']['all_writes_after_all_fetches'] for x in fields) else 'needs-timing-analysis',byte_writes=sum(x['cpu_glyph_byte_writes'] for x in fields),fields=fields,scope='Every selected CPU byte write is matched by address/count to an actual byte bus write. Non-displayed words pass whole-field exclusion; displayed words require ALL affected plane/row fetches before ANY affected write in the field. No fields or pixels ignored. Slot indices are chronological packed DMA records; adjacent fields delimit the next fetch.')
(p/'cpu-display-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(p.name,result['status'],result['byte_writes'])
