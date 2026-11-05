from pathlib import Path
import json,sys,struct
r=Path(__file__).resolve().parents[1];profile=sys.argv[1];a=r/'tmp/step5'/('c3-s1-'+profile+'-'+sys.argv[2]);b=r/'tmp/step5'/('c3-s1-'+profile+'-'+sys.argv[3]);blocks=json.loads((a/'blocks.json').read_text());width=sum(x['bytes'] for x in blocks)
x=(a/'records.bin').read_bytes();y=(b/'records.bin').read_bytes();assert len(x)==len(y)
# Same allocation and startup work: retain raw states, canonicalize only the
# exact native relocation columns and RNG pointers used by the B7 inventory.
from overlay_map import catalog
mp=json.loads((r/'manifest/step2-overlays.json').read_text());hunks={h['number']:h for g in mp['groups'] for h in g['hunks']}
columns={0x24fd0,0x24fd4}
for g in catalog():
 if g['header'] not in (0,0x22f30,0x30a30,0x30a7c):continue
 for h in g['hunks']:
  for offsets in h['reloc'].values():
   for off in offsets:columns.add(hunks[h['number']]['base']+off)
def normalize(data,path):
 rows=json.loads((path/'addresses.json').read_text());d=bytearray(data)
 for step in range(len(d)//width):
  cursor=0
  for block in blocks:
   addr=int(block['address'],16)
   for at in sorted(columns):
    if addr<=at and at+4<=addr+block['bytes']:
     offset=step*width+cursor+at-addr;v=struct.unpack_from('>I',d,offset)[0]
     for row in rows:
      if row['actual']<=v<row['actual']+row['size']:
       struct.pack_into('>I',d,offset,v-row['actual']+row['old']);break
   cursor+=block['bytes']
 return d
x=normalize(x,a);y=normalize(y,b);bad=[]
for step in range(len(x)//width):
 cursor=step*width
 for block in blocks:
  n=block['bytes']
  if x[cursor:cursor+n]!=y[cursor:cursor+n]:
   diff=[dict(address=hex(int(block['address'],16)+i),a=x[cursor+i],b=y[cursor+i]) for i in range(n) if x[cursor+i]!=y[cursor+i]]
   bad.append(dict(step=step+1,block=block['name'],differences=diff[:16]))
  cursor+=n
report=dict(status='passed' if not bad else 'failed',steps=len(x)//width,blocks=blocks,failures=bad,arms=[str(a),str(b)])
p=r/'manifest'/f'step5-c3-s1-{profile}-{sys.argv[2]}-{sys.argv[3]}.json';p.write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(bad),'mismatching blocks');print(json.dumps(bad[:12],indent=2))
