from pathlib import Path
import json,random,hashlib
r=Path(__file__).resolve().parents[1]
def fill(v,bits):
 out=0;c=0
 for i in range(bits):
  b=v>>i&1;out|=(b^c)<<i;c^=b
 return out

def test(raw,h):
 rows=[int.from_bytes(raw[y*48:(y+1)*48],'big') for y in range(200)]
 full=list(rows);narrow=list(rows);work=reads=bands=0
 for y in range(200-h,200):full[y]=fill(rows[y],384)
 for bottom in range(199,199-h,-16):
  top=max(200-h,bottom-15);width=0
  for y in range(bottom,top-1,-1):
   for w in range(24,width,-2):
    reads+=1
    if (rows[y]>>((24-w)*16))&0xffffffff:
     width=w;break
   if width==24:break
  if not width:continue
  bands+=1;work+=width*(bottom-top+1)
  for y in range(top,bottom+1):
   shift=(24-width)*16
   assert not rows[y]&((1<<shift)-1)
   narrow[y]=fill(rows[y]>>shift,width*16)<<shift
 assert full==narrow
 return dict(native_words=24*h,narrow_words=work,reads=reads,bands=bands)
rng=random.Random(9);cases=[]
for h in [1,15,16,17,100,103,106,199,200]:
 for mode in ['zero','full','sparse','odd','boundary']:
  for repeat in range(10):
   rows=[]
   for y in range(200):
    v=0
    if mode=='full':v=rng.getrandbits(384)
    elif mode=='sparse':v=sum(1<<rng.randrange(384) for _ in range(rng.randrange(5)))
    elif mode=='odd':v=1<<rng.randrange(384)
    elif mode=='boundary':v=1<<rng.choice([0,15,16,31,32,351,352,367,368,383])
    rows.append(v)
   test(b''.join(x.to_bytes(48,'big') for x in rows),h)
for p in (r/'tmp/step5').glob('h9-planes-*/result.json'):
 samples=json.loads(p.read_text()).get('samples',[])
 for n,x in enumerate(samples):
  for j in range(2):
   f=p.parent/f'plane-{n}-{j}.bin';raw=f.read_bytes();cases.append(dict(path=str(f.relative_to(r)),sha256=hashlib.sha256(raw).hexdigest(),**test(raw,x['height'])))
out=dict(status='passed',directed_cases=450,captured=cases,semantics='Descending exclusive fill, zero carry per row; right-only bounds retain odd carry; zero bands omitted; all 200 rows compared including untouched rows.')
(r/'manifest/render-h9-model.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
