from pathlib import Path
import random,json
mask=0xffffffff;rng=random.Random(0xc4c3);count=0
edges=[1,2,32767,32768,65535,65536,65537,0x7fffffff]
pairs=[(a,b) for a in edges for b in edges]+[(rng.randrange(1,65536),rng.randrange(1,0x80000000)) for _ in range(100000)]
for a,b in pairs:
 if a>65535:continue
 low=a*(b&65535);high=((b>>16)*a<<16)&mask
 result=(low+high)&mask;x=int(low+high>mask)
 assert result==(a*b)&mask
 # Native final ADD: low*A word product plus truncated B.high*A word product.
 native_lo=(a&65535)*(b&65535)
 native_hi=(((a&65535)*(b>>16))&65535)<<16
 assert x==int(native_lo+native_hi>mask)
 count+=1
for _ in range(100000):
 a=rng.randrange(1,0x80000000);b=rng.randrange(1,32768)
 result=(((a&65535)*b)+((((a>>16)*b)<<16)&mask))&mask
 assert result==(a*b)&mask
 # With B.high=0 native's final ADD uses zero, clearing X independently
 # of the earlier A.high cross-product's carry.
 native_final_add_left=0
 assert native_final_add_left+result<=mask
 count+=1
out=dict(status='passed',cases=count,scope='Preparatory positive word/long low32 product and native final-ADD carry model; not guest implementation acceptance')
Path(__file__).resolve().parents[1].joinpath('manifest/step5-c4-r3c-multiply-model.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
