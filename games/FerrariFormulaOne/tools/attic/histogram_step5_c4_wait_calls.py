from pathlib import Path
import sys,json,gzip,tempfile,shutil,os,collections
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev import barto
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5'/sys.argv[1]
fd,name=tempfile.mkstemp(dir=r/'tmp',prefix='ff1-wait-hist-',suffix='.bin');os.close(fd);temp=Path(name)
try:
 with gzip.open(p/'detail.bin.gz','rb') as a,temp.open('wb') as b:shutil.copyfileobj(a,b)
 t=barto.load(temp);rows=collections.defaultdict(lambda:dict(calls=0,stub_cycles=0));previous=None
 for f in t.fields:
  for pc,cost,regs in t.instructions(f):
   if pc==0x2a130:rows[previous]['calls']+=1;rows[previous]['stub_cycles']+=cost
   previous=pc
 out=dict(scope='Read-only planning: calls through patched native WaitBlit stub over all 100 fields; stub instruction cycles only, not a measured optimization.',trace=p.name,callers=[dict(pc=hex(pc),**v) for pc,v in sorted(rows.items(),key=lambda x:-x[1]['stub_cycles'])])
 (p/'wait-call-histogram.json').write_text(json.dumps(out,indent=2)+'\n')
 for v in out['callers']:print(v)
finally:temp.unlink()
