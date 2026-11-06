#!/usr/bin/env python3
"""Conservative local symbol hints: unique matching normalized instruction runs."""
import struct,json,sys,re,collections,bisect
from pathlib import Path
import replay_flight
from amigaxdev.disasm import records
p=Path(sys.argv[1]);file=replay_flight.ROOT/'tmp/game/TFX_v2.1_AGA/TFXAGA/data/TFX.040';d=file.read_bytes();pos=4
def w():
 global pos
 v=struct.unpack_from('>I',d,pos)[0];pos+=4;return v
assert w()==0
n,first,last=w(),w(),w();sizes=[w() for _ in range(last-first+1)];hs=[]
while pos<len(d):
 t=w()&0x3fffffff
 if t in [1001,1002]:
  size=w()*4;hs.append(dict(data=d[pos:pos+size],symbols=[]));pos+=size
 elif t==1003:hs.append(dict(data=b'\0'*(w()*4),symbols=[]))
 elif t==1004:
  while (n:=w()):w();pos+=4*n
 elif t==1008:
  while (n:=w()):
   name=d[pos:pos+n*4].rstrip(b'\0').decode('latin1');pos+=n*4;hs[-1]['symbols'].append((w(),name))
 elif t==1009:pos+=w()*4
 elif t!=1010:raise ValueError(t)
(p/'beta-code.bin').write_bytes(hs[0]['data'])
def ins(path,base,size):
 return [(o,re.sub(r'(?<![a-zA-Z])(?:0x[0-9a-f]+|-?\d+)', '#',text)) for o,raw,text in records(str(path),base,base,0,size,'68040') if text and not text.startswith('.short')]
base=json.loads((p/'segments.json').read_text())[0];new=ins(p/'entry-hunk0.bin',base,(p/'entry-hunk0.bin').stat().st_size)
index=collections.defaultdict(list);N=int(sys.argv[2]) if len(sys.argv)>2 else 16
for i in range(len(new)-N):index[tuple(x[1] for x in new[i:i+N])].append(new[i][0])
hints=[]
for hi in [0,5,6,12,14]:
 path=p/f'beta-code{hi}.bin';path.write_bytes(hs[hi]['data']);beta=ins(path,0,len(hs[hi]['data']));betai={o:i for i,(o,t) in enumerate(beta)}
 for o,name in hs[hi]['symbols']:
  if o not in betai:continue
  i=betai[o];match=index.get(tuple(x[1] for x in beta[i:i+N]),[])
  if len(match)==1:hints.append(dict(offset=match[0],name=name,beta_hunk=hi,beta_offset=o,matched_instructions=N))
(p/f'symbol-hints-{N}.json').write_text(json.dumps(sorted(hints,key=lambda x:x['offset']),indent=2))
print('Unique 16-instruction symbol hints',len(hints))
regions=json.loads((p/'region-costs.json').read_text());h=sorted(hints,key=lambda x:x['offset']);offs=[x['offset'] for x in h]
for off,c in sorted(regions.items(),key=lambda kv:-kv[1])[:40]:
 o=int(off,16);i=bisect.bisect_right(offs,o)-1;print(off, h[i] if i>=0 and h[i]['offset']==o else None)
# Retain symbol records for explicit manual hot-region review, not nearest-symbol attribution.
allsyms=[]
for hi in [0,5,6,12,14]:
 beta=ins(p/f'beta-code{hi}.bin',0,len(hs[hi]['data']));bi={o:i for i,(o,t) in enumerate(beta)}
 for o,name in hs[hi]['symbols']:
  if o in bi:allsyms.append(dict(name=name,hunk=hi,offset=o,ins=[t for _,t in beta[bi[o]:bi[o]+24]]))
(p/'beta-symbol-instructions.json').write_text(json.dumps(allsyms))
import difflib
ni={o:i for i,(o,t) in enumerate(new)}
for off,c in sorted(regions.items(),key=lambda kv:-kv[1])[:30]:
 o=int(off,16)
 if any(x['offset']==o for x in hints):continue
 if o not in ni:continue
 instr=[t for _,t in new[ni[o]:ni[o]+24]]
 best=sorted(((difflib.SequenceMatcher(None,instr,x['ins'],autojunk=False).ratio(),x) for x in allsyms),key=lambda x:-x[0])[:2]
 print('CANDIDATE',off,[(round(score,3),x['name'],x['hunk'],hex(x['offset'])) for score,x in best])
