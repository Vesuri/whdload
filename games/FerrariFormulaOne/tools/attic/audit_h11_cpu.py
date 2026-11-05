from pathlib import Path
import sys,json,struct,gzip,shutil,re,collections,bisect
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'));from amigaxdev import barto
p=Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());sy=r['symbols'];base=int(r['probe'],16)
def read(n):
 f=p/n
 return f.read_bytes() if f.exists() else gzip.open(str(f)+'.gz','rb').read()
m=read('start.bin');m+=bytes(0x200000-len(m))+read('start-fast.bin');c=read('canonical.bin');u=lambda a:struct.unpack_from('>I',m,a)[0]
font=struct.unpack_from('>I',c,0x216d8)[0];stride=2*struct.unpack_from('>H',c,0x2178c)[0];buf=base+sy['FF1RenderClockPixels'];assert buf>=0x200000
planes=[u(struct.unpack_from('>I',c,a)[0]+4*i) for a in [0x226ae,0x226b2] for i in range(3)]
allowed={a+y*48+x for a in planes for y in range(24,32) for x in [32,33,35,36,38,39,41]};assert max(allowed)<0x200000
listing=(Path(r['slave']).parent/'fine/fine.list').read_text();prep=set();copies={}
for v in re.finditer(r'^00:([0-9A-F]{8}) [0-9A-F]+\s+\d+[:R]\s+(.*)',listing,re.M):
 pc=int(v[1],16);s=v[2].strip()
 if sy['FF1RenderPrepareClock']<=pc<sy['FF1RenderOverlapHUD'] and s=='move.b (a0),(a1)':prep.add(base+pc)
 if sy['FF1RenderOverlapHUD']<=pc<sy['FF1RenderOverlapControl'] and s.startswith('move.b (a0)+,'):
  q=re.fullmatch(r'move.b \(a0\)\+,([0-9]*)\(a1\)',s);assert q,s;copies[base+pc]=int(q[1] or '0')
assert len(prep)==8 and len(copies)==7,(len(prep),len(copies))
raw=p/'detail.bin';temporary=not raw.exists()
if temporary:
 with gzip.open(str(raw)+'.gz','rb') as a,raw.open('wb') as b:shutil.copyfileobj(a,b)
t=barto.load(raw);pixels=bytearray(m[buf:buf+56]);expected=collections.Counter();actual=collections.Counter();prepares=0
for f in t.fields:
 for pc,cost,g in t.instructions(f):
  if pc in prep:
   assert font<=g[8]<font+stride*8 and buf<=g[9]<buf+56
   pixels[g[9]-buf]=m[g[8]];prepares+=1
  if pc in copies:
   src=g[8];dst=g[9]+copies[pc];assert buf<=src<buf+56 and dst in allowed
   expected[(dst,pixels[src-buf])]+=1
 for at in range(0,len(f.dma),f.dma_size):
  reg=struct.unpack_from('<H',f.dma,at)[0];addr=struct.unpack_from('<I',f.dma,at+12)[0];dat=struct.unpack_from('<Q',f.dma,at+2)[0];typ=struct.unpack_from('<h',f.dma,at+29)[0]
  if reg==0x1101:actual[(addr,dat&255)]+=1
  if typ in (3,4,5,6,7,8):assert not buf<=addr<buf+56
assert prepares and expected
assert all(actual[k]>=v for k,v in expected.items())
out=dict(status='passed',prepared_font_bytes=prepares,screen_byte_stores=sum(expected.values()),font=hex(font),workspace=hex(buf),workspace_bytes=56,workspace_in_fast=True,workspace_used_by_dma=False,screen_write_bounds='seven native clock columns, rows24..31, existing Chip planes',all_screen_stores_match_prepared_live_font=True,scope='Trace audit complements47 full-plane native comparisons; screen publication and original flag-before-clock order retained.')
(p/'h11-cpu-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out)
if temporary:raw.unlink()
