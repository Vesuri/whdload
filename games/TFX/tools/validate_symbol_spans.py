import map_symbols as m,json,bisect,collections
hs=m.load(m.GAME/'TFX.040');new=m.load(m.GAME/'tfx.020')[0];nd=new['data'];maps=json.loads((m.OUT/'block-maps.json').read_text());out=[]
newrel={o for v in new['relocs'].values() for o in v}
for h in [0,5,6,12,14]:
 old=hs[h];d=old['data'];rel={o for v in old['relocs'].values() for o in v};symbols=sorted(old['symbols']);ends=sorted(set(o for o,s in symbols)|{len(d)})
 mp={int(k):v['target'] for k,v in maps[f'beta-{h}'].items()};offs=sorted(mp)
 for start,name in symbols:
  end=ends[bisect.bisect_right(ends,start)];size=end-start
  if size<6:continue
  mask={i for o in rel if start<=o<end for i in range(o,o+4)};chunks=[];last=start
  for o in sorted(o for o in rel if start<=o<end):
   if o>last:chunks.append((last,d[last:o]))
   last=o+4
  if last<end:chunks.append((last,d[last:end]))
  anchor,pattern=max(chunks,key=lambda x:len(x[1]),default=(0,b''))
  if len(pattern)<8:continue
  hits=[];p=0
  while (p:=nd.find(pattern,p))>=0:
   target=p-(anchor-start);p+=1
   if target%2 or target<0 or target+size>len(nd):continue
   if any(d[x]!=nd[target+x-start] for x in range(start,end) if x not in mask):continue
   if any(target+o-start not in newrel for o in rel if start<=o<end):continue
   hits.append(target)
   if len(hits)>1:break
  if len(hits)==1:out.append(dict(name=name,beta_hunk=h,beta_offset=start,target=hits[0],size=size,evidence='complete symbol span identical except recorded relocations'))
(m.OUT/'exact-symbol-spans.json').write_text(json.dumps(out,indent=2));print('exact unique symbol spans',len(out))
for x in out:
 if any(k in x['name'] for k in ['Fill','Texture','Project','Polygon','Mono','Gen','depth','DrawObjects','SetColor','qdiv']):print(x)
