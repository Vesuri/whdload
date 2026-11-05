from pathlib import Path
import sys,json,re,gzip,tempfile,shutil,os,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1];j=json.loads((p/'result.json').read_text());probe=int(j['probe'],16);listing=(Path(j['slave']).parent/'fine.list').read_text()
points={};coeffs=collections.Counter();entry=probe+int(re.search(r'^FF1VelocityRotate000\s+00:([0-9A-F]+)',listing,re.M)[1],16)
for label in ('p2_xc_general','p2_zc_general'):
 s=listing[listing.index('.'+label+':'):];points[probe+int(re.search(r'00:([0-9A-F]{8})\s+[0-9A-F]+',s)[1],16)]=label
fd,name=tempfile.mkstemp(dir=r/'tmp',prefix='ff1-rotation-',suffix='.bin');os.close(fd);temp=Path(name)
try:
 with gzip.open(p/'detail.bin.gz','rb') as a,temp.open('wb') as b:shutil.copyfileobj(a,b)
 t=barto.load(temp);out={k:dict(calls=0,signed16=0,zero=0,values=collections.Counter()) for k in points.values()}
 for f in t.fields:
  for pc,cost,regs in t.instructions(f):
   if pc==entry:coeffs[(regs[0]&65535,regs[1]&65535)]+=1
   if pc not in points:continue
   v=regs[0];row=out[points[pc]];row['calls']+=1;row['signed16']+=v<=32767 or v>=0xffff8000;row['zero']+=v==0;row['values'][hex(v)]+=1
 for row in out.values():row['values']=row['values'].most_common(12)
 out['coefficients']=[dict(cos=a,sin=b,count=n) for (a,b),n in coeffs.most_common()]
 (p/'rotation-histogram.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
finally:temp.unlink()
