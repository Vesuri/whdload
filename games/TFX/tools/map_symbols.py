#!/usr/bin/env python3
"""Reproducible hunk extraction and bidirectional unique instruction-block matching.
Numbers are normalized only for candidate discovery; evidence retains original operands.
"""
import struct,json,re,collections,bisect,hashlib
from pathlib import Path
import replay_flight
from amigaxdev.disasm import records
ROOT=replay_flight.ROOT; OUT=ROOT/'tmp/step6'; GAME=ROOT/'tmp/game/TFX_v2.1_AGA/TFXAGA/data'
def load(path):
 d=path.read_bytes();p=4
 def w():
  nonlocal p
  v=struct.unpack_from('>I',d,p)[0];p+=4;return v
 assert w()==0
 n,first,last=w(),w(),w();sizes=[w() for _ in range(last-first+1)];hs=[]
 while p<len(d):
  t=w()&0x3fffffff
  if t in (1001,1002):
   size=w()*4;hs.append(dict(kind=t,data=d[p:p+size],symbols=[],relocs={}));p+=size
  elif t==1003:hs.append(dict(kind=t,data=bytes(w()*4),symbols=[],relocs={}))
  elif t==1004:
   while (n:=w()):
    target=w();hs[-1]['relocs'].setdefault(target,[]).extend(w() for _ in range(n))
  elif t==1008:
   while (n:=w()):
    name=d[p:p+n*4].rstrip(b'\0').decode('latin1');p+=n*4;hs[-1]['symbols'].append((w(),name))
  elif t==1009:
   size=w()*4;p+=size
  elif t!=1010:raise ValueError(t)
 return hs

def norm(s):return re.sub(r'(?<![a-zA-Z])(?:0x[0-9a-f]+|-?\d+)', '#',s)
def extract(name):
 hs=load(GAME/name);result=[]
 for i,h in enumerate(hs):
  path=OUT/f'{name}-{i}.bin';same=path.exists() and path.read_bytes()==h['data'];path.write_bytes(h['data']);cache=path.with_suffix('.json')
  if h['kind']==1001:
   if same and cache.exists():rs=json.loads(cache.read_text())
   else:
    rs=[(o,raw,text) for o,raw,text in records(str(path),0,0,0,len(h['data']),'68040') if text];cache.write_text(json.dumps(rs))
   result.append((i,rs))
 return hs,result

def blocks(a,b,N=12):
 aa=[norm(x[2]) for x in a];bb=[norm(x[2]) for x in b]
 ai=collections.defaultdict(list);bi=collections.defaultdict(list)
 for i in range(len(aa)-N+1):ai[tuple(aa[i:i+N])].append(i)
 for j in range(len(bb)-N+1):bi[tuple(bb[j:j+N])].append(j)
 seeds=sorted((ii[0],bi[k][0]) for k,ii in ai.items() if len(ii)==1 and len(bi.get(k,[]))==1)
 found=set();covered={}
 for i,j in seeds:
  if covered.get(i)==j:continue
  lo=0;hi=N
  while i+lo>0 and j+lo>0 and aa[i+lo-1]==bb[j+lo-1]:lo-=1
  while i+hi<len(aa) and j+hi<len(bb) and aa[i+hi]==bb[j+hi]:hi+=1
  found.add((i+lo,j+lo,hi-lo))
  for k in range(lo,hi):covered[i+k]=j+k
 return sorted(found)

def main():
 OUT.mkdir(exist_ok=True);beta,bcode=extract('TFX.040');plain,pcode=extract('TFX');target,tcode=extract('tfx.020');new=tcode[0][1]
 maps={};syms=[]
 for name,codes,hs in [('beta',bcode,beta),('plain',pcode,plain)]:
  for h,old in codes:
   bl=blocks(old,new);mapping=collections.defaultdict(set);ranges={}
   for i,j,n in bl:
    for k in range(n):mapping[old[i+k][0]].add(new[j+k][0]);ranges[old[i+k][0]]=(old[i][0],new[j][0],n)
   unique={o:next(iter(v)) for o,v in mapping.items() if len(v)==1}
   maps[f'{name}-{h}']={str(o):dict(target=v,block=ranges[o]) for o,v in unique.items()}
   if name=='beta':
    for o,s in hs[h]['symbols']:
     if o in unique:syms.append(dict(name=s,beta_hunk=h,beta_offset=o,target=unique[o],block=ranges[o]))
   print(name,h,'blocks',len(bl),'mapped',len(unique),'instructions',len(old))
 (OUT/'block-maps.json').write_text(json.dumps(maps,indent=2));(OUT/'candidate-symbols.json').write_text(json.dumps(syms,indent=2))
 (OUT/'inputs.json').write_text(json.dumps({n:hashlib.sha256((GAME/n).read_bytes()).hexdigest() for n in ['TFX','TFX.040','tfx.020']},indent=2))
 print('symbols',len(syms))
if __name__=='__main__':main()
