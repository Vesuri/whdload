from pathlib import Path
import json,re,struct,hashlib
r=Path(__file__).resolve().parents[1];old=r/'tmp/build/production-matched-pre-lifecycle';new=r/'tmp/build/production-matched';report={'status':'passed','scope':'After the passing four-profile matched-state run, coarse source/executable changes are limited to host linkage constants. Compare every payload byte after removing only explicitly assembled FF1_HOST_CODE_SIZE/ABORT immediates. No game-state field or native operand is excluded.','profiles':{}}
for kind in ['000','020']:
 arrays=[];sites=[]
 for root in [old,new]:
  raw=bytearray((root/kind/'payload.bin').read_bytes());listing=(root/kind/'fine.list').read_text();found=[]
  for m in re.finditer(r'^00:([0-9A-F]{8}) ([0-9A-F]+)\s+\d+:\s+(suba.l|adda.l) #FF1_HOST_(CODE_SIZE|ABORT),a2$',listing,re.M):
   at=int(m[1],16);width=len(m[2])//2-2;assert width in (2,4);found.append((at,m[4],int.from_bytes(raw[at+2:at+2+width],'big')));raw[at+2:at+2+width]=bytes(width)
  assert found;arrays.append(bytes(raw));sites.append(found)
 assert len(arrays[0])==len(arrays[1]) and arrays[0]==arrays[1],kind
 report['profiles'][kind]={'identical':True,'bytes':len(arrays[0]),'canonical_sha256':hashlib.sha256(arrays[0]).hexdigest(),'host_linkage_sites':sites}
(r/'manifest/production-coarse-identity.json').write_text(json.dumps(report,indent=2)+'\n');print('Both coarse payloads exact apart from explicit host linkage immediates')
