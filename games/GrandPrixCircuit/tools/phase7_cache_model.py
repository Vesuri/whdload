import sys,re,os,json,collections
from pathlib import Path
import _amigaxdev
from amigaxdev import barto
from gpc_report import regions
for name in ('moving-v7-a500','final-moving-4000','final-moving-6000'):
 p=Path(__file__).resolve().parents[1]/'tmp/phase7'/name;m=json.loads((p/'metadata.json').read_text());os.environ['SLAVE']=str(p/'slave.slave');sb=next(lo for lo,hi,n,o in regions((p/'before.bin').read_bytes(),m['base']) if n=='slave');s=(p/'slave.slave.lst').read_text(encoding='latin1');pc=sb+int(re.search(r'^render_angle\s+00:([0-9A-F]+)$',s,re.M)[1],16);keys=[]
 for f in (t:=barto.load(p/'trace.bin')).fields:
  for a,c,r in t.instructions(f):
   if a==pc:keys.append(r[4]&65535)
 print(name,len(keys),keys[:20])
 for size,shift in ((256,2),(256,4),(512,2),(512,3),(512,4),(1024,2),(1024,3),(1024,4),(1024,5),(2048,4)):
  cache={};miss=0
  for k in keys:
   if not k&255:continue
   ix=(k>>shift)&(size-1)
   if cache.get(ix)!=k:miss+=1;cache[ix]=k
  print(size,shift,miss)
