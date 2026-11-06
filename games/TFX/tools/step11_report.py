"""Current profile accounting, anchored to the exact build's assembler listing."""
import sys,csv,json,re,struct,collections
from pathlib import Path
p=Path(sys.argv[1]);listing=Path(sys.argv[2]);dev=Path(__file__).resolve().parents[1]
sym={m[1]:int(m[2],16) for m in re.finditer(r'^(\S+)\s+00:([0-9A-Fa-f]+)\s*$',listing.read_text(encoding='latin1'),re.M)}
rows=list(csv.reader((p/'profile.csv').open()));meta=list(map(int,rows[0][1:]));duration=meta[1]-meta[0]
pcs={int(r[1]):list(map(int,r[2:])) for r in rows if r[0]=='pc'}
residual=duration-sum(sum(v[1:5]) for v in pcs.values())
assert 0<=residual<=512, residual
base=json.loads((p/'segments.json').read_text())[0];code=(p/'entry-hunk0.bin').read_bytes();chip=(p/'chip.bin').read_bytes();fast=(p/'fast.bin').read_bytes()
def read(a,n):return chip[a:a+n] if a<0x200000 else fast[a-0x40000000:a-0x40000000+n]
def u32(a):return struct.unpack('>I',read(a,4))[0]
sb=struct.unpack_from('>I',code,0x19fe)[0]-sym['do_swap_screen']
assert read(sb+sym['do_swap_screen'],4)==bytes.fromhex('48e7fffe')
assert read(sb+sym['fast_buf'],4)!=bytes(4)
# Independent anchors reject a self-consistent but wrong swap-symbol offset.
for name in ['_drawdigit','_flushcache','fix_smc']:
 m=re.search(r'^00:'+f'{sym[name]:08X}'+r' ([0-9A-F]+)\s',listing.read_text(encoding='latin1'),re.M)
 assert m,name
 assert read(sb+sym[name],len(m[1])//2)==bytes.fromhex(m[1]),name
hot=json.loads((dev/'tmp/step6/hot-map.json').read_text());regions=[(int(h['profile_start'],16)+base,int(h['profile_end'],16)+base,h['name']) for h in hot if h['space']=='game hunk 0']
regions.append((sb+sym['do_swap_screen'],sb+sym['_drawdigit'],'slave screen copy/publication'))
totals=collections.Counter({'observer boundary residual':residual});top=[]
for pc,v in pcs.items():
 cost=v[1]+v[2]+v[4];name=next((n for a,b,n in regions if a<=pc<b),'other game' if base<=pc<base+len(code) else 'other slave' if sb<=pc<sb+sym['_drawdigit']+0x10000 else 'other')
 totals[name]+=cost;totals['interrupt/dispatch overhead']+=v[3]
 top.append(dict(pc=hex(pc),game_offset=hex(pc-base),slave_offset=hex(pc-sb),instructions=v[0],ticks=cost,percent=100*cost/duration))
ex=u32(4);cache={name:pcs.get(u32(ex-off+2),[0])[0] for name,off in [('CacheClearU',636),('CacheClearE',642),('CacheControl',648)]}
cache['slave flush']=pcs.get(sb+sym['_flushcache'],[0])[0];cache['font SMC flush']=pcs.get(sb+sym['fix_smc'],[0])[0];cache['cache opcodes']=sum(int(r[-1]) for r in rows if r[0]=='cache')
fpu_cost=sum(v[1]+v[2]+v[4] for pc,v in pcs.items() if int.from_bytes(read(pc,2),'big')&0xfe00==0xf200)
counts=json.loads((p/'counts.json').read_text());assert counts['publications']==meta[2]
result=dict(publications=meta[2],duration=duration,unattributed_boundary_ticks=residual,fpu_instruction_percent=100*fpu_cost/duration,strict_fpu=meta[4],slave_base=sb,symbols=sym,cache=cache,fpu_exceptions=sum(int(r[-1]) for r in rows if r[0]=='exception' and int(r[2]) in [11,48,49,50,51,52,53,54,55]),regions=[dict(name=n,ticks=t,percent=100*t/duration) for n,t in totals.most_common()],top_pcs=sorted(top,key=lambda x:-x['ticks']),chip_reads=sum(v[9] for v in pcs.values()),chip_writes=sum(v[10] for v in pcs.values()))
assert sum(totals.values())==duration
(p/'step11-report.json').write_text(json.dumps(result,indent=2))
print('Publications',meta[2],'cache',cache,'FPU exceptions',result['fpu_exceptions'])
for r in result['regions']:
 if r['percent']>=.5:print(r['name'],round(r['percent'],3))
