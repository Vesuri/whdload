import sys,json,struct,collections
from harness_a import *
from drive import barto
s=Session(sys.argv[1]);rows=[]
try:
 route(s)
 for cell in range(0x432,0x462,4):
  ptr=rd(s,cell);orig=rd(s,ptr-4);count=rd(s,ptr,2)
  rows.append(dict(owner=hex(cell),public=ptr,original=orig,count=count,size=2+14*count))
 for site,orig in [(0xb0520,0x19a7e),(0xb032c,0x38c84),(0xafe94,0x5c2cc)]:
  ptr=rd(s,site+2);count=rd(s,ptr,2)
  rows.append(dict(owner=hex(site),public=ptr,original=orig,count=count,size=2+14*count))
 for r in rows:
  assert 0x200000<=r['public']<0xa00000 and r['count']>0
  data=read_bytes(s,r['public'],r['size']);pixels=[int.from_bytes(data[i:i+4],'big') for i in range(2,len(data),14)]
  assert all(0<=p<0x100000 for p in pixels),r
  r['pixel_range']=[min(pixels),max(pixels)]
 p=s.out/'dma.bin';s.cmd(f'monitor profile 99 "" "{p}"',timeout=120);trace=barto.load(str(p));hits=collections.Counter()
 for f in trace.fields:
  for i in range(0,len(f.dma),f.dma_size):
   a=struct.unpack_from('<I',f.dma,i+12)[0];kind=struct.unpack_from('<h',f.dma,i+29)[0]
   if kind in (0,2):continue
   for r in rows:
    for domain in ['original','public']:
     if r[domain]<=a<r[domain]+r['size']:hits[(r['owner'],domain,kind,a)]+=1
 (s.out/'race.png').write_bytes(trace.fields[-1].shot)
 result=dict(headers=rows,dma_header_reads=[dict(owner=o,domain=d,kind=k,address=hex(a),count=c) for (o,d,k,a),c in hits.items()]);(s.out/'headers.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True);assert all(o=='0x446' and d=='original' and k==7 and a in (0x467c,0x467e) for o,d,k,a in hits)
 car=next(r for r in rows if r['owner']=='0x446')
 assert read_bytes(s,car['public'],4)==read_bytes(s,car['original'],4)
finally:s.quit()
