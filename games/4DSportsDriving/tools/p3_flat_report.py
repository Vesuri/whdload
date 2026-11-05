import bisect,collections,json,re,struct,sys
from pathlib import Path
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());raw=(p/'memory.bin').read_bytes();mem=m['memory_base'];g=m['game_base'];sl=m['slave_base']
syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
labels={sl+v:n for n,v in syms.items() if n.startswith(('raster_','perf_','sim_'))}
for i in range(0,0x3a04c-2,2):
 if raw[g-mem+i:g-mem+i+2]==bytes.fromhex('4e55'):labels[g+i]=f'game_{i:05x}'
lines=(p/'flat-profile.txt').read_text().splitlines();meta={a[0]:a[1] for line in lines if (a:=line.split()) and len(a)==2};total=int(meta['units'])
for line in lines:
 a=line.split()
 if a[0]=='N':
  pc=int(a[3],16)
  if g<=pc<g+0x3a04c:labels.setdefault(pc,f'game_{pc-g:05x}')
starts=sorted(labels);counts=collections.defaultdict(lambda:[0,0,0,0]);pcrows=[]
for line in lines:
 a=line.split()
 if a[0]!='P':continue
 pc,cycles,n,chip,access=int(a[1],16),*map(int,a[2:]);j=bisect.bisect_right(starts,pc)-1
 if g<=pc<g+0x3a04c or sl<=pc<sl+struct.unpack_from('>I',(p/'slave.slave').read_bytes(),28)[0]*4:
  name=labels[starts[j]] if j>=0 else 'unknown'
  if name.startswith('raster_solid_fast_'):name='raster_solid_fast_writers'
 else:name='other'
 for k,v in enumerate((cycles,n,chip,access)):counts[name][k]+=v
 pcrows.append((cycles,hex(pc),name,n))
rows=[dict(name=k,percent=round(v[0]/total*100,3),cycles=v[0],instructions=v[1],chip_percent=round(v[2]/total*100,3),chip_accesses=v[3]) for k,v in sorted(counts.items(),key=lambda x:-x[1][0])]
r=dict(meta=meta,rows=rows,top_pcs=sorted(pcrows,reverse=True)[:40]);(p/'flat-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(rows[:30],indent=2))
