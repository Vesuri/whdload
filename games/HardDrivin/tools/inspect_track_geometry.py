from pathlib import Path
import json,struct
p=Path('tmp/prof/c3-final-straight-a500');meta=json.loads((p/'metadata.json').read_text());a4=meta['layout']['a4'];banks=[(0,(p/'timing-state-chip.bin').read_bytes()),(0xc00000,(p/'timing-state-slow.bin').read_bytes())]
def mem(a,n):
 for base,b in banks:
  if base<=a and a+n<=base+len(b):return b[a-base:a-base+n]
 raise ValueError(hex(a))
def global_(o,fmt):return struct.unpack('>'+fmt,mem(a4+o-65536,struct.calcsize('>'+fmt)))[0]
output={}
for name,po,co in [('main',0x98e0,0x98e8),('stunt',0x9952,0x9956)]:
 ptr=global_(po,'I');count=global_(co,'H');rows=[]
 for i in range(count):
  r=struct.unpack('>10h',mem(ptr+i*20,20));rows.append(dict(index=i,left=r[:3],right=r[3:6],rest=r[6:],center=[(r[a]+r[a+3])/2 for a in range(3)]))
 output[name]=rows
 print(name,count,'elevated',[(r['index'],r['center'],r['rest']) for r in rows if r['center'][1]!=0])
for name,po,co in [('main',0x998a,0x998e),('stunt',0x9994,0x9998)]:
 ptr=global_(po,'I');count=global_(co,'H');print(name,'waypoints',[struct.unpack('>4h',mem(ptr+8*i,8)) for i in range(count)])
Path('tmp/track-geometry.json').write_text(json.dumps(output,indent=2)+'\n')
