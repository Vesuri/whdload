"""Validate provenance and summarize within-CPU executable comparisons."""
import json,re,hashlib
from pathlib import Path
r=Path(__file__).resolve().parents[1]/'tmp/exe-compare'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for cpu in ['020','020-68881','030','060']:
 for tape in ['action','follow']:
  paths=[r/f'{cpu}-{tape}-{v}' for v in ['integer','newfpu']]
  m=[read(p/'manifest.json') for p in paths];c=[read(p/'counts.json') for p in paths]
  for k in ['slave_sha256','emulator_sha256','tape_sha256','fpsp040_sha256','fpsp060_sha256']:assert m[0][k]==m[1][k],k
  for p in paths:assert sha(p/'slave.slave')==sha(r/'render.slave')
  assert all(x['pal_fields']==2000 for x in c)
  assert [x['variant']['custom3'] for x in m]==[1,3]
  assert all(x['variant']['custom4']==18 for x in m)
  info=[dict(re.findall(r'(\w+)=(\w+)',(p/'cpuinfo-entry.txt').read_text())) for p in paths]
  assert info[0]==info[1],info
  assert read(paths[1]/'renderer-audit.json')['passed']
  code=(paths[1]/'renderer-code.bin').read_bytes()
  meta=read(r.parent/'step9/fpu-sites.json');offsets=[x['offset'] for x in meta['sites']]+[0x50f82,0x51682,0x5169e,0x516b6,0x517a4,0x517f2,0x5183c]
  if cpu=='060':
   old=(r.parent/'step13/candidate-060/060-newfpu/code.bin').read_bytes()
   assert all(code[o:o+4]==old[o:o+4] for o in offsets)
  else:assert all(code[x['offset']:x['offset']+4]==bytes.fromhex(x['original']) for x in meta['sites'])
  a,b=[x['publications'] for x in c]
  rows.append(dict(cpu=cpu,tape=tape,integer=a,newfpu=b,change_percent=100*(b/a-1),cpuinfo=info[0],fpu_sites_checked=len(offsets)))
(r/'comparison.json').write_text(json.dumps(rows,indent=2)+'\n')
for row in rows:print(row['cpu'],row['tape'],row['integer'],row['newfpu'],round(row['change_percent'],2))
