import json,struct,math
from pathlib import Path
root=Path('tmp');results={};alltests=[]
def truncprod(v,f):return math.trunc(v*f/65536)
def y(track,cam,correct):
 s=cam>>16;f=cam&65535;h=track[((s+correct)&255)*2+1];d=-truncprod(h,f);ys=[]
 for j in range(3):ys.append(93-d);d+=track[((s+j+1)&255)*2+1]
 pos=cam+32768;j=(pos>>16)-s;frac=pos&65535;delta=ys[j]-ys[j+1];interp=ys[j]-((abs(delta)*frac+32768)//65536)*(1 if delta>=0 else -1)
 return 76+math.trunc(interp*256/384)
for tag in ['on-long','off-long','original-long']:
 p=root/('h1-'+tag);rows=json.load(open(p/'trace.json'));model=json.load(open(p/'model.json'));seen=set();tests=[]
 for r in rows:
  b=bytes.fromhex(r['state']);s=struct.unpack_from('>I',b,30)[0]>>16;t=struct.unpack('>512b',bytes.fromhex(r['track']));key=(s,t)
  if key in seen:continue
  seen.add(key);cam=(s<<16)+65535
  test=dict(segment=s,slope=t[(s&255)*2+1],next_slope=t[((s+1)&255)*2+1],native=[y(t,cam,0),y(t,cam+1,0)],candidate=[y(t,cam,1),y(t,cam+1,1)])
  tests.append(test)
 results[tag]=dict(frames=len(model),boundaries=len(tests),max_native=max(abs(x['native'][1]-x['native'][0]) for x in tests),max_candidate=max(abs(x['candidate'][1]-x['candidate'][0]) for x in tests),cases=[x for x in tests if x['segment'] in [45,381,395,396,397,583]])
 alltests+=tests
print(json.dumps(results,indent=2));(root/'h1-evaluation.json').write_text(json.dumps(results,indent=2))
