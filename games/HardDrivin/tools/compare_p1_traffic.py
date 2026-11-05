from pathlib import Path
import json,struct
root=Path('tmp/prof');names=['s4-traffic-reference','p1-traffic8'];data=[]
for name in names:
 p=root/name;m=json.loads((p/'metadata.json').read_text());first=(p/'before.bin').read_bytes();actors=[struct.unpack_from('>I',first,i*46+8)[0] for i in range(m['count'])];streams=[]
 for k in ['before','after']:
  raw=bytearray((p/(k+'.bin')).read_bytes())
  for off in range(0,len(raw),46):
   for j in [0,4]:
    ptr=struct.unpack_from('>I',raw,off+j)[0];struct.pack_into('>I',raw,off+j,(ptr-m['route_base'])&0xffffffff if ptr else 0)
   actor=struct.unpack_from('>I',raw,off+8)[0];assert actor==actors[(off//46)%m['count']];struct.pack_into('>I',raw,off+8,(off//46)%m['count'])
  streams.append(bytes(raw))
 streams.append((p/'poses.bin').read_bytes());data.append(streams)
for i,k in enumerate(['before','after','poses']):
 assert data[0][i]==data[1][i],(k,next((j for j,(a,b) in enumerate(zip(data[0][i],data[1][i])) if a!=b),None))
r=dict(passed=True,reference=names[0],candidate=names[1],records=1440,full_before_after_records=True,poses=True,pointer_normalization='Route offsets and verified stable actor identities only');(root/names[1]/'native-equivalence.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
