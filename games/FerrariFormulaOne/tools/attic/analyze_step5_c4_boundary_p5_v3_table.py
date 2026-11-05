from pathlib import Path
import json,re,struct,hashlib
r=Path(__file__).resolve().parents[1];reports=[]
for arm in ['baseline-render','candidate']:
 p=r/f'tmp/step5/c4-boundary-p5-v3-ab-a500-{arm}';j=json.loads((p/'result.json').read_text());probe=int(j['probe'],16)
 listing=(r/'tmp/build/step5-c4-boundary-p5-v3-ab-verify/000/fine.list').read_text();off=int(re.search(r'^C4BoundaryCoefficients\s+00:([0-9A-F]+)',listing,re.M)[1],16);rows=json.loads((p/'addresses.json').read_text())
 def actual(old):
  row=next(x for x in rows if x['old']<=old<x['old']+x['size']);return row['actual']+old-row['old']
 checks=[]
 for stage in ['anchor','end']:
  low=(p/f'{stage}-raw.bin').read_bytes();slow=(p/f'{stage}-raw-slow.bin').read_bytes()
  def read(addr,n):return slow[addr-0xc00000:addr-0xc00000+n] if addr>=0xc00000 else low[addr:addr+n]
  raw=b''.join(read(actual(0x2180c+i*2),2) for i in range(1280));native=struct.unpack('>1280h',raw);expected=b''.join(struct.pack('>h',(x*1000)//32768) for x in native);table=read(probe+off,2560)
  assert len(table)==2560 and table==expected,(arm,stage)
  checks.append({'stage':stage,'native_sha256':hashlib.sha256(raw).hexdigest(),'table_sha256':hashlib.sha256(table).hexdigest()})
 assert checks[0]['native_sha256']==checks[1]['native_sha256'] and checks[0]['table_sha256']==checks[1]['table_sha256']
 reports.append({'arm':arm,'entries':1280,'checks':checks,'address':hex(probe+off)})
out={'status':'passed','scope':'Every native Q15 coefficient independently scaled with signed floor division; covers all 1024 sine/cosine angle pairs. Table and native input unchanged across 100 updates in each arm.','arms':reports}
(r/'manifest/step5-c4-p5-v3-table.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
