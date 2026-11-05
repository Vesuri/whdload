from pathlib import Path
import re,struct,json,sys
b=Path(sys.argv[1]);code=(b/'fine.bin').read_bytes();listing=(b/'fine.list').read_text()
sy={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',listing,re.M)}
rows=[]
for m in re.finditer(r'^00:([0-9A-F]{8})\s+[0-9A-F]+\s+\d+:\s*(.*)$',listing,re.M):
 rows.append((int(m[1],16),m[2]))
spans=[]
for i,(pc,src) in enumerate(rows):
 if pc>=sy.get('public_install_boundary',sy['public_begin_early']):continue
 if sy['selection_path']<=pc<sy['selection_interval']+4:continue
 m=re.search(r'\b(ds\.[bwl]|dc\.[bwl])\s+(.*)',src)
 if not m:continue
 expr=m[2].split(';')[0].strip()
 if m[1].startswith('dc.'):
  if not all(x.strip()=='0' for x in expr.split(',')):continue
  size={'b':1,'w':2,'l':4}[m[1][-1]]*len(expr.split(','))
 else:
  size=next(p for p,_ in rows[i+1:] if p>pc)-pc
 assert size>0 and code[pc:pc+size]==bytes(size),(hex(pc),src,size)
 spans.append(dict(offset=pc,size=size,source=src))
(b/'reset.json').write_text(json.dumps(spans,indent=2)+'\n')
(b/'reset.bin').write_bytes(b''.join(struct.pack('>II',x['offset'],x['size']) for x in spans)+struct.pack('>I',0xffffffff))
print('Reset',len(spans),'explicit zero-initialized data spans')
