from pathlib import Path
import math,random,re,json
r=Path(__file__).resolve().parents[1]
s=(r.parents[1]/'Games/FerrariFormulaOne_Sqrt.s').read_text().split('FF1RootSeeds:',1)[1].split('        else',1)[0]
t=[int(x,16) for x in re.findall(r'\$([0-9a-f]{4})',s)];assert len(t)==1024
rng=random.Random(481);values=[0,2**64-1]
for k in range(256,1024):
 for n in (k<<54,((k+1)<<54)-1,(k<<54)+(1<<53)):
  for shift in range(0,64,2):values.append(n>>shift)
for _ in range(1000000):
 n=rng.getrandbits(64);root=math.isqrt(n);values.extend((n,root*root,max(0,root*root-1)))
max_correction=0
for n in values:
 if not n:continue
 shift=(64-n.bit_length())//2;x=n<<(shift*2);hi=x>>32
 k=x>>54;base=t[k];slope=(t[k+1] if k<1023 else 65536)-base
 seed=min(0xffffffff,(base<<16)+slope*((hi>>6)&65535)+131072)
 if shift:seed=(seed>>shift)+1
 assert seed>=math.isqrt(n)
 if n>>32>=seed:answer=0xffffffff;correction=0
 else:
  answer=(seed+n//seed)//2;expected=math.isqrt(n)
  correction=answer-expected;assert 0<=correction<=5
  while answer*answer>n:answer-=1
 assert answer==math.isqrt(n)
 max_correction=max(max_correction,correction)
result=dict(status='passed',cases=len(values),max_correction=max_correction,table_entries=len(t))
(r/'manifest/step5-b5-seed-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
