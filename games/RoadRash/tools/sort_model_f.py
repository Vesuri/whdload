import json
from pathlib import Path
rows=json.loads(Path('tmp/f-sort-probe/sort.json').read_text());prev=[];tot=[0,0,0,0];samples=[]
def before(x,y):return bool((x-y)&0x80000000)
for r in rows:
 keys=r['keys'];n=len(keys);out=[];nc=nm=0
 for i,k in enumerate(keys):
  j=0
  while j<len(out):
   nc+=1
   if before(k,keys[out[j]]):break
   j+=1
  nm+=2*(len(out)-j+1);out.insert(j,i)
 seed=[i for i in prev if i<n]+[i for i in range(n) if i not in prev];sc=sm=0
 for j in range(1,n):
  v=seed[j];pos=j
  while pos:
   sc+=1;u=seed[pos-1]
   if not(before(keys[v],keys[u]) or keys[v]==keys[u] and v<u):break
   seed[pos]=u;sm+=1;pos-=1
  seed[pos]=v;sm+=1
 assert seed==out
 # seed gather/permutation publication + final sorted-key and ordinal outputs.
 sm+=3*n
 for i,v in enumerate([nc,nm,sc,sm]):tot[i]+=v
 samples.append(dict(field=r['field'],n=n,native_compares=nc,native_stores=nm,seed_compares=sc,seed_stores=sm));prev=out
print(dict(native_comparisons=tot[0],native_stores=tot[1],seed_comparisons=tot[2],seed_stores=tot[3],frames=len(rows)))
Path('tmp/f-sort-model.json').write_text(json.dumps(dict(totals=tot,samples=samples),indent=2))
