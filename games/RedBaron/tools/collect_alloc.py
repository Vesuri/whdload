"""Read the completed private allocation marker from the owned VERIFY process."""
import argparse,json,struct,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from allocation_census import decode,summarize
p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args()
r.locate();blob=Path('tmp/build/route-ram.bin').read_bytes();base=r.DUMP_BASE;hits=[];at=0
while (at:=blob.find(b'RBALLOC1',at))>=0:
 h=struct.unpack_from('>9I',blob,at+8)
 if base<=h[3]<base+len(blob):hits.append((base+at,h))
 at+=8
assert len(hits)==1,hits
address,h=hits[0];count,overflow,active,buffer,ex,oa,of,capacity,stride=h
assert count<=capacity and not overflow and not active,h
r.command(f'gdb dump binary memory {a.out}/alloc.bin {buffer:#x} {buffer+count*stride:#x}')
header=blob[address-base:address-base+44];(a.out/'alloc-header.bin').write_bytes(header)
rows=decode(header,(a.out/'alloc.bin').read_bytes());result=summarize(rows)
(a.out/'allocation-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print('records',result['records'],'peak spill',result['peak_spill_bytes'],'live spill',result['live_spill_bytes'],flush=True)
