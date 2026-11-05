#!/usr/bin/env python3
import hashlib,json,os,struct,sys
from pathlib import Path
from gpc_report import regions
out=Path(sys.argv[1]);base=int(sys.argv[2],0);d=(out/'before.bin').read_bytes()
r={n:lo for lo,hi,n,o in regions(d,base)}
markers=[];i=-1
while (i:=d.find(b'GPCVERIFY\0',i+1))>=0:
 if struct.unpack_from('>II',d,i+10)==(r['gpc'],1):markers.append(i)
assert len(markers)==1, 'live VERIFY marker missing/ambiguous'
v=struct.unpack_from('>6IH',d,markers[0]+10)
m=dict(base=base,code_base=r['gpc'],data_base=r['gpc-data'],marker=base+markers[0],epoch=v[2],races=v[3],joy_calls=v[4],cacr=v[5],last_joy=v[6],slave_sha256=hashlib.sha256((out/'slave.slave').read_bytes()).hexdigest(),options={k:os.environ.get(k) for k in ('AMIGA_MODEL','CPU','CHIP_KB','FAST_KB','SLOW_KB','KICKSTART','WHD_ARGS','EXTRA_ARGS','DETERMINISTIC','JOY0','JOY1','SKIP_FIELDS','FIELDS')})
(out/'metadata.json').write_text(json.dumps(m,indent=2)+'\n')
print('anchor epoch',m['epoch'],'CACR',hex(m['cacr']),'races',m['races'])
