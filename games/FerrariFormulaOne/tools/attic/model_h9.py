from pathlib import Path
import json,struct
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5/h9-planes-040-40-bce-grid';s=json.loads((p/'result.json').read_text())
def fill(row):
 carry=0;out=0
 for bit in range(384):
  v=(row>>bit)&1;out|=(v^carry)<<bit;carry^=v
 return out
for n,x in enumerate(s['samples']):
 print('sample',n,'height',x['height'],'caller',x['caller'])
 for j in range(2):
  b=(p/f'plane-{n}-{j}.bin').read_bytes();rows=[int.from_bytes(b[y*48:(y+1)*48],'big') for y in range(200)]
  active=[(y,384-v.bit_length(),383-((v&-v).bit_length()-1),v.bit_count()%2) for y,v in enumerate(rows) if v and y>=200-x['height']]
  print('plane',j,'rows',len(active),'odd',sum(a[3] for a in active),'bounds',[(lo,min((a[1] for a in active if lo<=a[0]<lo+16),default=384)//16,max((a[2] for a in active if lo<=a[0]<lo+16),default=-1)//16) for lo in range(96,200,16)])
  bad=[y for y in range(200-x['height']) if rows[y]]
 print('firstcoord',list(x['coords'].items())[:2])
 if n==0:pass
