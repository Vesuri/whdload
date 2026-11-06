#!/usr/bin/env python3
"""Auditable self-cost regions and independent counters; never invent symbol names."""
import csv,json,sys,re,struct,bisect,collections,hashlib
from pathlib import Path
p=Path(sys.argv[1]);root=Path(__file__).resolve().parents[1]
rows=list(csv.reader((p/'profile.csv').open()));meta=list(map(int,rows[0][1:]));duration=meta[1]-meta[0]
pcs={int(r[1]):list(map(int,r[2:])) for r in rows if r[0]=='pc'}
assert duration>0 and sum(sum(v[1:5]) for v in pcs.values())==duration
assert all(len(v)==13 and all(n>=0 for n in v) for v in pcs.values())
bases=json.loads((p/'segments.json').read_text());base=bases[0];code=(p/'entry-hunk0.bin').read_bytes();counts=json.loads((p/'counts.json').read_text())
assert counts['window']==[2,252] and counts['publications']==meta[2]==57 and meta[3]==45
chip=(p/'chip.bin').read_bytes();fast=(p/'fast.bin').read_bytes()
def read(a,n):return chip[a:a+n] if a<0x200000 else fast[a-0x40000000:a-0x40000000+n]
def u32(a):return struct.unpack('>I',read(a,4))[0]
# Identify FPSP loaded code by many exact signatures, rejecting preload copies with no execution.
f=(p/'fpsp040').read_bytes();o=f.find(bytes.fromhex('000003e9'));n=struct.unpack_from('>I',f,o+4)[0]*4;fc=f[o+8:o+8+n];votes=collections.Counter()
for off in range(0,n-32,128):
 sig=fc[off:off+32]
 if len(set(sig))<8:continue
 pos=fast.find(sig)
 while pos>=0:votes[0x40000000+pos-off]+=1;pos=fast.find(sig,pos+1)
candidates=[a for a,v in votes.items() if v>100 and any(a<=pc<a+n for pc in pcs)]
assert len(candidates)==1;fb=candidates[0]
# Exact slave relocation anchor, from patched swap call and verified assembler listing.
sb=struct.unpack_from('>I',code,0x19fe)[0]-0x20b8
assert read(sb+0x218e,8)==bytes.fromhex('20d920d920d920d9')
names={int(x['offset']):x['name'] for x in json.loads((p/'symbol-hints-16.json').read_text())}
manual={0x4e53a:('CPU masked sprite merge','rendering'),0x3b93a:('SuperShape view dispatcher (descriptive)','rendering'),0x60bfc:('polygon bounds / edge preparation','rendering'),0x4e6b4:('_DrawMonoImage (slave patch anchor)','rendering'),0x77c8:('aircraft list update loop','game logic'),0x249a:('RGB palette blend loop','rendering'),0x5f252:('left polygon edge generator','rendering'),0x5f1e0:('right polygon edge generator','rendering'),0x5f124:('paired polygon edge walker','rendering'),0x4bdca:('integer square root','maths'),0x4b774:('matrix angle helper','maths'),0x3f51e:('shape handle address lookup','rendering'),0x3bc56:('nested SuperShape dispatcher (descriptive)','rendering'),0x3d032:('SuperShape part evaluation','rendering'),0x7d90:('aircraft iterator, table DBF8','game logic'),0x7d54:('aircraft iterator, table DB30','game logic'),0x39cac:('viewport scale calculation','rendering'),0x5765e:('SetColor / shape command region','rendering')}
starts={base}|{int(r[2]) for r in rows if r[0]=='call' and base<=int(r[2])<base+len(code)}
for off in range(0,len(code)-3,2):
 if code[off:off+2] in [b'\x4e\x55',b'\x4e\x56']:starts.add(base+off)
starts=sorted(starts);regions={}
# Region endpoints are observed call targets or compiler prologues, not guessed nearest symbols.
for i,a in enumerate(starts):
 off=a-base;name=names.get(off,f'routine ${off:05x}');cat='unclassified game'
 if 0x55b6c<=off<0x62408 or 0x62408<=off<0x64c00 or 0x6a4b8<=off<len(code):cat='rendering'
 if re.search('Draw|Plot|Sprite|Shape|Color|Colour|Pal|Line|Screen|View|Project|Cone',name,re.I):cat='rendering'
 if re.search('flight_computer|gbased|alien|ally|missile|Control|UseLevel',name,re.I):cat='game logic'
 if name in ['_qdiv'] or re.search('^_(sin|cos|tan|atan|asin|acos|sqrt|log|exp)',name):cat='maths'
 if off in manual:name,cat=manual[off]
 regions[a]=dict(start=hex(off),end=hex((starts[i+1] if i+1<len(starts) else base+len(code))-base),name=name,category=cat,ticks=0,instructions=0,chip_reads=0,chip_writes=0,chip_read_bytes=0,chip_write_bytes=0)
external=collections.Counter();totals=collections.Counter();fpsp_cost=0
for pc,v in pcs.items():
 selfcost=v[1]+v[2]+v[4];totals['interrupt/other dispatch overhead']+=v[3]
 if base<=pc<base+len(code):
  r=regions[starts[bisect.bisect_right(starts,pc)-1]];r['ticks']+=selfcost;r['instructions']+=v[0]
  for key,idx in [('chip_reads',9),('chip_writes',10),('chip_read_bytes',11),('chip_write_bytes',12)]:r[key]+=v[idx]
  totals[r['category']]+=selfcost
 else:
  if fb<=pc<fb+n:cat='FPSP';fpsp_cost+=selfcost
  elif sb<=pc<sb+0x10000:cat='slave'
  else:cat='OS / other'
  totals[cat]+=selfcost;external[pc]=selfcost
regions=[dict(r,percent=100*r['ticks']/duration) for r in regions.values() if r['instructions']]
# Known slave routine regions: copy/publication, line/sprite helpers and remaining support.
copy=sum(v[1]+v[2]+v[4] for pc,v in pcs.items() if sb+0x20b8<=pc<sb+0x2202)
totals['slave']-=copy;totals['rendering']+=copy
regions.append(dict(start='slave:$20b8',end='slave:$2202',name='do_swap_screen / fast-to-chip screen copy',category='rendering',ticks=copy,percent=100*copy/duration))
asset_targets={int(r[2]) for r in rows if r[0]=='call' and int(r[1])==base+0x3816}
assert len(asset_targets)==1;asset=next(iter(asset_targets))
assert read(asset,8)==bytes.fromhex('4e56000048e73e20')
asset_cost=sum(v[1]+v[2]+v[4] for pc,v in pcs.items() if asset<=pc<asset+0xd8)
totals['OS / other']-=asset_cost;totals['rendering']+=asset_cost
regions.append(dict(start='loaded image:$0',end='loaded image:$d8',name='planar image drawing code called at game:$3816',category='rendering',ticks=asset_cost,percent=100*asset_cost/duration))
assert sum(totals.values())==duration
ops={0x0e:'FSIN',0x1d:'FCOS',0x0f:'FTAN',0x0a:'FATAN',0x0c:'FASIN',0x03:'FINTRZ'}
trap=collections.Counter();frames=collections.defaultdict(collections.Counter);irq=collections.Counter()
for r in rows:
 if r[0]!='exception':continue
 frame,vector,pc,op,num=map(int,r[1:]);irq[vector]+=num
 if vector in [11,48,49,50,51,52,53,54,55]:
  ext=struct.unpack('>H',read(pc+2,2))[0];name=ops.get(ext&127,hex(ext&127));key=(hex(pc-base),name,hex(op),hex(ext));trap[key]+=num;frames[frame][f'{name}@{pc-base:x}']+=num
assert sum(trap.values())==(2394 if meta[4] else 0)
# Count actual handler entry, not merely exceptions. Entry table is in the FPSP file itself.
entry_counts={}
for vector in [11,48,49,50,51,52,53,54,55]:
 needle=struct.pack('>I',vector);matches=[]
 for off in range(0,n-8,2):
  if read(fb+off,4)==needle:
   target=u32(fb+off+4)
   if fb<=target<fb+n:matches.append(target)
 if matches:entry_counts[str(vector)]=[dict(offset=hex(t-fb),executions=pcs.get(t,[0])[0]) for t in matches]
assert entry_counts['11'][0]['executions']==sum(trap.values())
ex=u32(4);cache={}
for name,off in [('CacheClearU',636),('CacheClearE',642),('CacheControl',648)]:
 assert read(ex-off,2)==b'\x4e\xf9';cache[name]=pcs.get(u32(ex-off+2),[0])[0]
cache['slave _flushcache']=pcs.get(sb+0x14ec,[0])[0];cache['F4xx cache opcodes']=sum(int(r[-1]) for r in rows if r[0]=='cache')
summary=dict(window=counts['window'],publications=57,fpu_no_unimplemented=meta[4],raw_ticks=duration,instructions=sum(v[0] for v in pcs.values()),cost_coverage=1.0,phases={k:sum(v[i] for v in pcs.values()) for k,i in [('fetch',1),('body',2),('special',3),('padding',4)]},categories={k:dict(ticks=v,percent=100*v/duration) for k,v in totals.items()},chip={k:sum(v[i] for v in pcs.values()) for k,i in [('reads',9),('writes',10),('read_bytes',11),('write_bytes',12)]},fpsp=dict(base=fb,size=n,signature_votes=votes[fb],self_ticks=fpsp_cost,percent=100*fpsp_cost/duration,entries=entry_counts,sites=[dict(site=k[0],opcode=k[1],words=k[2:],count=v,per_publication=v/57) for k,v in trap.items()],per_frame={k:dict(v) for k,v in frames.items()}),exceptions=dict(irq),cache=cache,regions=sorted(regions,key=lambda r:-r['ticks']))
with (p/'fpsp-per-frame.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['frame','opcode_site','entries'])
 for frame,values in sorted(frames.items()):
  for site,count in sorted(values.items()):w.writerow([frame,site,count])
with (p/'cache-per-frame.csv').open('w') as f:
 w=csv.writer(f);w.writerow(['frame','flush_calls'])
 assert not any(cache.values())
 for frame in range(0,58):w.writerow([frame,0])
(p/'profile-report.json').write_text(json.dumps(summary,indent=2))
with (p/'routine-costs.csv').open('w') as f:
 fields=['start','end','name','category','ticks','percent','instructions','chip_reads','chip_writes','chip_read_bytes','chip_write_bytes'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(summary['regions'])
print(json.dumps({k:v for k,v in summary.items() if k not in ['regions','fpsp']},indent=2));print('FPSP',summary['fpsp']['sites']);print('HOT >=0.5%')
for r in summary['regions']:
 if r['percent']>=.5:print(r['start'],r['name'],round(r['percent'],3))
