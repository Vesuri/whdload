from pathlib import Path
import re,json,collections
p=Path('tmp/d-bus-priority-tail-build/RoadRash.lst');records=[];file=None;cur=None
for line in p.read_text(encoding='latin1').splitlines():
 m=re.match('Source: "(.*)"',line)
 if m:file=m[1];cur=None;continue
 m=re.match(r'^00:([0-9A-F]+)\s+([0-9A-F]+)\s+([0-9]+):\s?(.*)$',line)
 if m:
  cur=dict(file=file,line=int(m[3]),address=int(m[1],16),data=m[2],source=m[4]);records.append(cur);continue
 m=re.match(r'^00:([0-9A-F]+)\s+([0-9A-F]+)\s*$',line)
 if m and cur and int(m[1],16)==cur['address']+len(cur['data'])//2:cur['data']+=m[2]
refs=[]
for r in records:
 if not (Path('src')/str(r['file'])).exists():continue
 b=bytes.fromhex(r['data']);hits=[]
 for off in range(0,len(b)-3,2):
  v=int.from_bytes(b[off:off+4],'big')
  if 0x80000<=v<0xbc3ec:hits.append([off,hex(v)])
 if hits:refs.append(dict(**r,hits=hits))
Path('tmp/d-original-hunk/slave-native-refs.json').write_text(json.dumps(refs,indent=2)+'\n')
print('rows',len(refs),'operands',sum(len(x['hits']) for x in refs));print(collections.Counter(r['file'] for r in refs));print([(r['source'],r['hits']) for r in refs if not re.search(r'\$[89aAbB][0-9a-fA-F]{4}',r['source'])][:40])
